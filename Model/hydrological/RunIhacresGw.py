"""
Python wrapper for Rachel Blaker's IhacresGW hydrological model of Maules Creek

Michael Asher michael.james.asher@gmail.com
February 2015
"""
from rpy2.robjects import FloatVector
from rpy2.robjects.packages import SignatureTranslatedAnonymousPackage
import os
# import pandas
import csv
import numpy as np

def run_hydrology(init_gwstorage, init_C, init_Nash, init_Qq, init_Qs):

	r_path = os.path.join(os.path.dirname(__file__), 'WrappableRunIhacresGw.R')
	with open(r_path) as r_file:

		"""
		import .R file and call function
		"""
		string = r_file.read()
		IhacresGW = SignatureTranslatedAnonymousPackage(string, "IhacresGW")
		workingdir = os.path.dirname(__file__)
		# workingdir = "~/Dropbox/integrated/Mike/hydrological"
		# datadir = workingdir + "/Maules_19690101_20100302"

		datadir = workingdir + "/data"
		# sim, tdat = IhacresGW.RunIhacresGw(workingdir, datadir)
		return IhacresGW.RunIhacresGw(workingdir, datadir, init_gwstorage, init_C, FloatVector(init_Nash), init_Qq, init_Qs)


# get state so model can be stopped and started
def get_state(hydro_sim, hydro_tdat, hydro_mod, state_index):

	# original_flow = np.array(hydro_sim.rx2('Q')).squeeze()
	original_gwstorage = np.array(hydro_sim.rx2('G')).squeeze()[:,0]
	original_raw_C = np.array(hydro_sim.rx2('raw_C')).squeeze()
	original_next_Nash = np.array(hydro_sim.rx2('next_Nash')).squeeze()
	original_Qq = np.array(hydro_sim.rx2('Qq')).squeeze()
	original_Qs = np.array(hydro_sim.rx2('Qs')).squeeze()

	return original_gwstorage[state_index-1], original_raw_C[state_index-1], FloatVector(original_next_Nash[state_index-1]), original_Qq[state_index-1], original_Qs[state_index-1] # RunIhacresGw.R takes about 17 seconds

# extract data from hydrological model output
def get_outputs(hydro_sim, hydro_tdat, hydro_mod):
	gw_i = 3
	gwlevel = -np.array(hydro_sim.rx2('Glevel').rx2('gw_shallow'))[:,gw_i] # 3rd col varies most
	flow = np.array(hydro_sim.rx2('Q')).squeeze()
	gwstorage = np.array(hydro_sim.rx2('G')).squeeze()[:,0]
	dates = list(hydro_tdat.rx2('dates'))
	gwfitparams = -np.array(hydro_mod.rx2('param').rx2('gwFitParam').rx2('gw_shallow'))[gw_i,:]

	return dates, flow, gwlevel, gwstorage, gwfitparams

def write_csv(filename, rows):
	with open(filename, 'w') as csvfile:
		writer = csv.writer(csvfile)
		for row in rows:
			writer.writerow(row)

def read_csv(filename):
	rows = []
	with open(filename, 'r') as csvfile:
		reader = csv.reader(csvfile)
		for row in reader:
			rows.append(row)
	return rows


"""
inline editing of csv input files
"""

def set_climate_data(dates, rainfall, temperature, swextraction, gwextraction):

	datadir = os.path.dirname(__file__) +'/data/'
	timesteps = len(dates)

	dates = list(dates)

	write_csv(
		datadir+'swextraction.data.csv', 
		# zip(['date']+dates, ['sw_419051']+[0 for i in range(timesteps)] )
		zip(['date']+dates, ['sw_419051']+list(swextraction) )
		)

	write_csv(
		datadir+'gwextraction.data.csv', 
		# zip(['date']+dates, ['gw_shallow']+[0 for i in range(timesteps)], ['gw_deep']+[0 for i in range(timesteps)] )
		zip(['date']+dates, ['gw_shallow']+list(gwextraction), ['gw_deep']+[0 for i in range(timesteps)] )
		)

	write_csv(
		datadir+'rain.data.csv', 
		zip(['date']+dates, ['sw_419051']+list(rainfall) )
		)

	write_csv(
		datadir+'temperature.data.csv', 
		zip(['date']+dates, ['sw_419051']+list(temperature) )
		)

	write_csv(
		datadir+'swinflow.data.csv', 
		zip(['date']+dates, ['None']+[0 for i in range(timesteps)] )
		)


# from tempfile import NamedTemporaryFile
# import shutil
# import csv

# filename = 'data/swextraction.data.csv'
# tempfile = NamedTemporaryFile(delete=False)

# with open(filename, 'rb') as csvFile, tempfile:
#     reader = csv.reader(csvFile, delimiter=',', quotechar='"')
#     writer = csv.writer(tempfile, delimiter=',', quotechar='"')

#     for row in reader:
#         row[1] = row[1]
#         writer.writerow(row)



# r_file = open('WrappableRunIhacresGw.R')


"""
inline editing of csv input files
"""

# data_path = os.path.join(os.path.dirname(__file__), 'data/swextraction.data.csv')
# swextraction = pandas.read_csv(data_path, index_col='date')
# swextraction['sw_419051'][2] = 0.2
# swextraction['sw_419051']['2010-02-23'] = 0.2
# swextraction.to_csv(data_path)
