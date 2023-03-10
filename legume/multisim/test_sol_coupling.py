### G Louarn 9/03/2023 / exemples input sol et couplage plante-sol
# a mettre dans modele sol...

import os
import sys

try:
    import legume

    path_ = os.path.dirname(os.path.abspath(legume.__file__))  # local absolute path of L-egume
except:
    path_ = r'C:\devel\l-egume\legume'  # r'C:\devel\grassland'

print(('path', path_))

sys.path.insert(0, path_)

try:
    from .soil3ds import soil_moduleN as solN #import de la version develop si module soil3ds est installe
    #import soil_moduleN3 as solN
except:
    import soil_moduleN3 as solN #soil_moduleN2_bis as solN #! renommer car dans nouvelle version Lpy, mot module est reserve et fait planter!


import IOxls
import IOtable
import run_legume_usm as runl
import numpy as np
import initialisation as initial
import RootDistrib as rtd


#################
## exemple 1: initialisation sol personalisee en n couches + fonctionnement VGL 'Local Transporter' avec racines homogenes
#################

# lecture des parametre sol directement a partir d'un fichier sol
# personalisation des initialisations (sol personnalise / creation solN)
# loop de 100 jours avec option 'Local Transporter' pour plant uptake

foldin =  os.path.join(path_, 'input')
fxls_sol = 'Parametres_sol_exemple.xls'
ongletS = 'lusignan99'

path_sol = os.path.join(path_,foldin,fxls_sol)
par_SN, par_sol = IOxls.read_sol_param(path_sol, ongletS)

# initialisation taille scene / discretisation (1D - homogene pour ttes les couches)
cote = 100 #cm
pattern8 = [[0, 0], [cote, cote]]
Lsol = max((pattern8[1][0] - pattern8[0][0]) / 100., (pattern8[1][1] - pattern8[0][1]) / 100.)  # m
largsol = min((pattern8[1][0] - pattern8[0][0]) / 100., (pattern8[1][1] - pattern8[0][1]) / 100.)  # m
surfsolref = Lsol * largsol  # m2
dz_sol = 5. #cm
ncouches_sol = 20
discret_solXY = [1,1] #nombre de voxel selon X et Y
lims_sol = rtd.lims_soil(pattern8, dxyz=[[Lsol / discret_solXY[0]] * discret_solXY[0], [largsol / discret_solXY[1]] * discret_solXY[1], [dz_sol / 100.] * ncouches_sol])


# vecteurs pour initialisation des propietes des couches de sol
vsoilnumbers = [1]*ncouches_sol #numeros de sol du profil -> mesures acsyd11
vDA = [1.31]*ncouches_sol #densite apparente de sol (mesure pesees initial aschyd11)
vMO = [par_SN['MO0_30']]*ncouches_sol
vCN = [par_SN['CN0_30']]*ncouches_sol
vARGIs = [par_SN['ARGIs']]*ncouches_sol
vCALCs = [par_SN['CALCs']]*ncouches_sol
vNH4 = [2.]*ncouches_sol # #!! kg d'N.ha-1 (entree de STICS)
vNO3 = [2.]*ncouches_sol # kg d'N.ha-1 (entree de STICS)
HRpinit = [] #default


# lecture meteo / mng journaliere = fixe
meteo_j = {'TmoyDay': 11., 'RG': 846.7, 'Et0': 2.0, 'Precip': 0., 'Tmin': '', 'Tmax': '', 'Tsol': 10., 'I0': 47.04, 'durjour': 10.88}
mng_j = {'Coupe': 0.0, 'Irrig': 0.0, 'FertNO3': 0.0, 'FertNH4': 0.0, 'Hcut': 3.0, 'ForceNNI': 1.0}
Tsol = meteo_j['Tsol']


# options pour simul sol
opt_residu = 0 #sans residus a mineraliser
opt_Nuptake = 1 #Local Transporters


#############
#init de l'objet sol
S = solN.SoilN(par_sol, par_SN, soil_number=vsoilnumbers,
                   dxyz=[[Lsol / discret_solXY[0]] * discret_solXY[0], [largsol / discret_solXY[1]] * discret_solXY[1],
                         [dz_sol / 100.] * ncouches_sol], vDA=vDA, vCN=vCN, vMO=vMO, vARGIs=vARGIs, vNO3=vNO3,
                   vNH4=vNH4, vCALCs=vCALCs, Tsol=Tsol, pH=par_SN['pH'], ZESX=par_SN['ZESX'], CFES=par_SN['CFES'],
                   obstarac=None, pattern8=pattern8)

#init variables memoire evaporation
Uval = par_SN['q0']
stateEV = [0., 0., 0.]  # pour le calcul de l'evaporation du sol (memoire du cumul evapore depuis derniere PI)
HXs = par_sol[str(vsoilnumbers[0])]['teta_fc']  # humidite a la capacite au champ de l'horizon de surface
b_ = solN.bEV(par_SN['ACLIMc'], par_SN['ARGIs'], HXs)



###### Creation variables plante entree pour simul plante-sol: ls_epsi / ls_roots / concentration N racine ou NNI = fixes
nb_plt = 200 #nombre de plantes dans pattern8
ls_epsi = [0.5/200]*nb_plt #fration de espsi.plant-1 (equivalent a transmis de 50%)
MSrac_plt = np.array([10./200]*nb_plt) #g plt-1 (equivalent a 1 T.ha-1)
SRL = 250 #m.g-1
LENrac_plt = MSrac_plt*SRL #m.plt-1
ls_N = np.array([0.75]*nb_plt)#invar['NNI']

#calcul de ls_roots adapte format sol S avec distribution homogene dans tout le sol
ls_roots = [] # cm !!
for i in range(nb_plt):
    #longueur de racine
    rootLen_i = S.m_1 * LENrac_plt[i]/ncouches_sol*100
    ls_roots.append(rootLen_i)

#np.sum(ls_roots[0])
#LENrac_plt[0]

#lecture parametre plante ParamP utilise dans les calculs du sol
path_plante = os.path.join(path_,foldin,'Parametres_plante_exemple.xls')#'Parametres_plante_v5cLucas.xls')#'Parametres_plante_v18.xls')#'Parametres_plante_v9Lucas_debugL.xls')#r'H:\devel\grassland\grassland\L-gume\Parametres_plante_v5cLucas.xls'
ongletP = 'Fix2'
g4 = IOxls.read_plant_param(path_plante, ongletP)
ParamP = [g4]*nb_plt
#utilise pourquoi / quel param precisement utilise dans le sol? -> revoir pour rendre explicite


######### loop pour n_jour
n_jour = 100
for j in range(n_jour):
    meteo_j = {'TmoyDay': 11., 'RG': 846.7, 'Et0': 2.0, 'Precip': 0., 'Tmin': '', 'Tmax': '', 'Tsol': 10., 'I0': 47.04, 'durjour': 10.88}
    mng_j = {'Coupe': 0.0, 'Irrig': 0.0, 'FertNO3': 0.0, 'FertNH4': 0.0, 'Hcut': 3.0, 'ForceNNI': 1.0}

    # Step Sol avec les inputs prevues dans VGL
    tag_inputs_soil_step = [S, par_SN, surfsolref, stateEV, Uval, b_, meteo_j, mng_j, ParamP, ls_epsi, ls_roots, ls_N, opt_residu, opt_Nuptake]  # input tag
    S, stateEV, ls_ftsw, ls_transp, ls_Act_Nuptake_plt, temps_sol = solN.step_bilanWN_solVGL(*tag_inputs_soil_step)


    #print de sorties N
    kgNO3solHa = S.m_NO3.sum() / S.surfsolref*10000
    kgNH4solHa = S.m_NH4.sum() / S.surfsolref * 10000
    kgNsolHa = kgNO3solHa + kgNH4solHa
    uptNO3PltHa = ls_Act_Nuptake_plt[0].sum()*nb_plt/S.surfsolref*10000
    lix = S.lixiNO3  # /S.surfsolref*10000

    cumMinN_j = S.bilanN['cumMinN'][-1]
    Lix_j = S.bilanN['cumLix'][-1]
    UptakePlt_j = S.bilanN['cumUptakePlt'][-1].sum()
    azomes = S.bilanN['azomes'][-1]
    MinN = S.bilanN['cumMinN'][-1]

    print('N', j, azomes, kgNO3solHa, kgNH4solHa, Lix_j, MinN, UptakePlt_j)
    # print('N', j, azomes,kgNsolHa, kgNO3solHa,kgNH4solHa, lix, Lix_j, uptNO3PltHa, UptakePlt_j)

    # print de sorties W
    transp = sum(ls_transp)
    tsw = S.tsw_t.sum()

    #print('Water', j, tsw,transp)





#################
## exemple 2: initialisation sol avec fonction l-py a partir liste usm + fonctionnement VGL 'Local Transporter' avec racines homogenes
#################

# lecture des parametre sol directement a partir d'un fichier sol
# lecture initialisations / meteo / mng a partir du numero d'usm
# loop de 100 jours avec option 'Local Transporter' pour plant uptake


###### Lecture parametres sol depuis un fichier USM de VGL et initialisation objet sol avec fonction init VGL

#lecture des parametre sol a partir de la liste des usm
foldin =  os.path.join(path_, 'input')
#foldout = os.path.join(path_, 'output')
fxls = 'liste_usms_exemple.xls'
ongletBatch = 'exemple'
IDusm = 1711

usms_path = os.path.join(path_, foldin, fxls)
usms = IOxls.xlrd.open_workbook(usms_path)
ls_usms = IOtable.conv_dataframe(IOxls.get_xls_col(usms.sheet_by_name(ongletBatch)))
ls_usms['ID_usm'] = list(map(int, ls_usms['ID_usm']))
id = ls_usms['ID_usm'].index(IDusm)
#mylsys = runl.lsystemInputOutput_usm(fxls, foldin=foldin, ongletBatch=ongletBatch, i=id, path_OUT=foldout)
fxls_sol = ls_usms['sol'][id]
ongletS = ls_usms['ongletS'][id]
fxls_ini = ls_usms['inis'][id]
ongletIn = ls_usms['ongletIn'][id]
fxls_mng = ls_usms['mng'][id]
ongletMn = ls_usms['ongletMn'][id]
fxls_Met = ls_usms['meteo'][id]
ongletMet = ls_usms['ongletM'][id]
fxls_Plt = ls_usms['plante'][id]
ongletP = ls_usms['ongletP'][id]

path_sol = os.path.join(path_,foldin,fxls_sol)
path_inis = os.path.join(path_,foldin,fxls_ini)
path_met = os.path.join(path_,foldin,fxls_Met)
path_mng = os.path.join(path_,foldin,fxls_mng)
path_plante = os.path.join(path_,foldin,fxls_Plt)

par_SN, par_sol = IOxls.read_sol_param(path_sol, ongletS)
inis = IOxls.read_plant_param(path_inis, ongletIn)
met = IOxls.read_met_file(path_met, ongletMet)
mng = IOxls.read_met_file(path_mng, ongletMn)


#meteo / mng journalier
DOY = 50 #DOYdeb
meteo_j = IOxls.extract_dataframe(met, ['TmoyDay','RG','Et0','Precip','Tmin','Tmax','Tsol'], 'DOY', val=DOY)
mng_j = IOxls.extract_dataframe(mng, ['Coupe','Irrig', 'FertNO3','FertNH4','Hcut'], 'DOY', val=DOY)
for k in list(meteo_j.keys()): meteo_j[k] = meteo_j[k][0]
for k in list(mng_j.keys()): mng_j[k] = mng_j[k][0]

# options pour simul sol
opt_residu = 0 #sans residus a mineraliser
opt_Nuptake = 1 #Local Transporters


###### Creation objet sol avce fonction init_sol_fromLpy utilisee dans vgl
cote = 100 #cm
pattern8 = [[0, 0], [cote, cote]]
Lsol = max((pattern8[1][0] - pattern8[0][0]) / 100., (pattern8[1][1] - pattern8[0][1]) / 100.)  # m
largsol = min((pattern8[1][0] - pattern8[0][0]) / 100., (pattern8[1][1] - pattern8[0][1]) / 100.)  # m
surfsolref = Lsol * largsol  # m2
dz_sol = inis['dz_sol']
discret_solXY = list(map(int, inis['discret_solXY']))
ncouches_sol = int(inis['ncouches_sol'])
lims_sol = rtd.lims_soil(pattern8, dxyz=[[Lsol / discret_solXY[0]] * discret_solXY[0], [largsol / discret_solXY[1]] * discret_solXY[1], [dz_sol / 100.] * ncouches_sol])


#initialisation du sol avec fonction pour Lpy (sans residus)
S, Tsol, Uval, stateEV, b_ = initial.init_sol_fromLpy(inis, meteo_j, par_sol, par_SN, Lsol, largsol, discret_solXY, dz_sol, pattern8, opt_residu=0)

## initialisation matrice des residus -> faut en plus des parameres plantes!
# vCC = initial.init_plant_residues_fromParamP(S, opt_residu, ParamP)
# ls_groupe_resid = list(map(int, riri.get_lsparami(ParamP, 'groupe_resid')))
# setr = list(set(ls_groupe_resid)) #set equivalent fonction r.unique!
# ls_mat_res = []
# for i in range(2): #force a 2 sinon bug qd des esidu de l'esp 1 seulement #len(setr)):
#     ls_mat_res = ls_mat_res + [0.*S.m_1, 0.*S.m_1, 0.*S.m_1, 0.*S.m_1]


###### Creation variables plante entree pour simul plante-sol: ls_epsi / ls_roots / concentration N racine ou NNI = fixes
nb_plt = 200 #nombre de plantes dans pattern8
ls_epsi = [0.5/200]*nb_plt #fration de espsi.plant-1 (equivalent a transmis de 50%)
MSrac_plt = np.array([10./200]*nb_plt) #g plt-1 (equivalent a 1 T.ha-1)
SRL = 250 #m.g-1
LENrac_plt = MSrac_plt*SRL #m.plt-1
ls_N = np.array([0.75]*nb_plt)#invar['NNI']

#calcul de ls_roots adapte format sol S avec distribution homogene dans tout le sol
ls_roots = [] # cm !!
for i in range(nb_plt):
    #longueur de racine
    rootLen_i = S.m_1 * LENrac_plt[i]/(ncouches_sol*discret_solXY[0]*discret_solXY[1])*100
    ls_roots.append(rootLen_i)


#lecture parametre plante ParamP utilise dans les calculs du sol
g4 = IOxls.read_plant_param(path_plante, ongletP)
ParamP = [g4]*nb_plt
#utilise pourquoi / quel param precisement utilise dans le sol? -> revoir pour rendre explicite


######### loop pour n_jour
n_jour = 100
for j in range(n_jour):
    DOY+=1
    meteo_j = IOxls.extract_dataframe(met, ['TmoyDay', 'RG', 'Et0', 'Precip', 'Tmin', 'Tmax', 'Tsol'], 'DOY', val=DOY)
    mng_j = IOxls.extract_dataframe(mng, ['Coupe', 'Irrig', 'FertNO3', 'FertNH4', 'Hcut'], 'DOY', val=DOY)
    for k in list(meteo_j.keys()): meteo_j[k] = meteo_j[k][0]
    for k in list(mng_j.keys()): mng_j[k] = mng_j[k][0]

    # Step Sol avec les inputs prevues dans VGL
    tag_inputs_soil_step = [S, par_SN, surfsolref, stateEV, Uval, b_, meteo_j, mng_j, ParamP, ls_epsi, ls_roots, ls_N, opt_residu, opt_Nuptake]  # input tag
    S, stateEV, ls_ftsw, ls_transp, ls_Act_Nuptake_plt, temps_sol = solN.step_bilanWN_solVGL(*tag_inputs_soil_step)


    #print de sorties N
    kgNO3solHa = S.m_NO3.sum() / S.surfsolref*10000
    kgNH4solHa = S.m_NH4.sum() / S.surfsolref * 10000
    kgNsolHa = kgNO3solHa + kgNH4solHa
    uptNO3PltHa = ls_Act_Nuptake_plt[0].sum()*nb_plt/S.surfsolref*10000
    lix = S.lixiNO3  # /S.surfsolref*10000

    cumMinN_j = S.bilanN['cumMinN'][-1]
    Lix_j = S.bilanN['cumLix'][-1]
    UptakePlt_j = S.bilanN['cumUptakePlt'][-1].sum()
    azomes = S.bilanN['azomes'][-1]
    MinN = S.bilanN['cumMinN'][-1]

    print('N', DOY, azomes, kgNO3solHa, kgNH4solHa, Lix_j, MinN, UptakePlt_j)
    # print('N', DOY, azomes,kgNsolHa, kgNO3solHa,kgNH4solHa, lix, Lix_j, uptNO3PltHa, UptakePlt_j)

    # print de sorties W
    transp = sum(ls_transp)
    tsw = S.tsw_t.sum()

    #print('Water', DOY, tsw,transp)





#################
## exemple 3:
#################

#to do: refaire avec formalisme uptake plante romain


# + revoir sol  modele
# retire initialisation pour : pH=par_SN['pH'], ZESX=par_SN['ZESX'], CFES=par_SN['CFES'] -> lu dans parSN!
# revoir initialisation memoire en interne
# Uval = par_SN['q0']
# stateEV = [0., 0., 0.]  # pour le calcul de l'evaporation du sol (memoire du cumul evapore depuis derniere PI)
# HXs = par_sol[str(vsoilnumbers[0])]['teta_fc']  # humidite a la capacite au champ de l'horizon de surface
# b_ = solN.bEV(par_SN['ACLIMc'], par_SN['ARGIs'], HXs)
