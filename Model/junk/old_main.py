import numpy as np

from climate.read_climate import read_climate_projections

from hydrological.RunIhacresGw import set_climate_data, run_hydrology

from farm_decision.farm_optimize import maximum_profit, load_crops

from ecological.ecological_indices import calculate_water_index

'''
inputs: climate scenario, crop prices, WUE, irrigation area, AWD (function that determines fraction of limits based on levels)
outputs: farm profit, profit variability, water levels (from which we compute environmental indices)
'''

def model(
		  dates,
		  rainfall,
	      temperature,
	      crops,
	      WUE,
	      farm_area,
	      AWD
	      ):

	# write rainfall and temperature to csv files
	# -------------------------------------------
	# write to rainfall, temparture, extractions for given time range
	
	max_i = 3000
	extractions = [0 for i in dates]
	set_climate_data(dates=dates[:max_i], rainfall=rainfall[:max_i], temperature=temperature[:max_i], swextraction=extractions[:max_i], gwextraction=extractions[:max_i])

	# run hydrological model 
	# -------------------------------------------
	# hydro_sim, hydro_tdat, hydro_mod = run_hydrology() # RunIhacresGw.R takes about 17 seconds
	hydro_sim, hydro_tdat, hydro_mod = run_hydrology(0, 
												422.7155/2, # d/2
												[0,0], # must be of length NC
												0, 
												0) 

	gw_i = 3
	gwlevel = -np.array(hydro_sim.rx2('Glevel').rx2('gw_shallow'))[:,gw_i] # 3rd col varies most
	flow = np.array(hydro_sim.rx2('Q')).squeeze()
	gwstorage = np.array(hydro_sim.rx2('G')).squeeze()[:,0]
	dates = list(hydro_tdat.rx2('dates'))
	gwfitparams = -np.array(hydro_mod.rx2('param').rx2('gwFitParam').rx2('gw_shallow'))[gw_i,:]

	# interpolated_gwlevel = map(lambda x: x*gwfitparams[0] + gwfitparams[1], gwstorage)
	# assert np.alltrue(interpolated_gwlevel == gwlevel)

	print 'gwstorage',gwstorage
	print 'gwlevel',gwlevel
	print 'flow',flow
	# print 'dates',dates

	# TODO
	# use gwlevel and flow from above to adjust AWD then update extractions, rerun 
	# run a year at a time!!

	# apply AWD to get water_licence
	# -------------------------------------------
	# Extraction limit 2,200 ML/yr \cite{Upper_and_Lower_Namoi_Groundwater_Sources}
	# Maules Creek Entitlement (ML/year) 1,413 \cite{Namoi_Unregulated_and_Alluvial}
	water_limit = {"sw_unregulated": 1413, "gw": 2200}

	water_licence = {}
	for licence_type in water_limit:
		water_licence[licence_type] = water_limit[licence_type] * AWD[licence_type]

	# run LP farmer decision model
	# -------------------------------------------
	total_water_licence = water_licence['sw_unregulated']+water_licence['gw']
	farm_profit = maximum_profit(crops, farm_area, total_water_licence)

	# subtract water used by farmer from flows
	# -------------------------------------------
	# TODO
	# run a year at a time
	gwstorage = gwstorage - water_limit['gw']/365.0
	interpolated_gwlevel = map(lambda x: x*gwfitparams[0] + gwfitparams[1], gwstorage)
	flow = flow - water_limit['sw_unregulated']/365.0

	import matplotlib.pyplot as plt 
	plt.plot(gwlevel)
	plt.plot(interpolated_gwlevel)
	plt.show()

	# run ecological model 
	# -------------------------------------------
	water_index = calculate_water_index(interpolated_gwlevel, flow, dates)

	return farm_profit, water_index

if __name__ == '__main__':

	all_crops = load_crops()

	# Water allocations for the Namoi Valley
	# Available Water Determination Order for Various NSW Groundwater Sources (No. 1) 2014
	# http://www.water.nsw.gov.au/Water-management/Water-availability/Water-allocations/Available-water-determinations
	# TODO 
	# this should ideally be a function of gwlevel and flow?
	AWD = {"sw_unregulated": 1, "gw": 1}

	# Comparative Irrigation Costs 2012 - NSW DPI (Peter Smith)
	# TODO 
	# does nothing
	WUE = {"flood_irrigation": 0.65, "spray_irrigation": 0.8, "drip_irrigation": 0.85}

	# \cite{powell2011representative}
	farm_area = {"flood_irrigation": 782, "spray_irrigation": 0, "drip_irrigation": 0, "dryland": 180}

	climate_dates, rainfall, PET = read_climate_projections('climate/419051.csv', scenario=1)
	# TODO
	# get climate projections temp not PET
	temperature = PET * 5


	farm_profit, water_index = model(
	      climate_dates,
		  rainfall,
	      temperature,
	      all_crops,
	      WUE,
	      farm_area,
	      AWD
	      )

	print "PROFIT", farm_profit
	print "WATER", np.min(water_index), np.mean(water_index), np.max(water_index)







'''
===========================================
Potential research questions
===========================================
'''


'''
Climate: sensitivity of profit to WUE under different climate scenarios
'''

'''
Prices: sensitivity of profit to price and WUE
'''

'''
Adaptability: sensitivity of profit variability to WUE
'''

'''
Environmental: sensitivity of environmental indices to WUE and irrigation area 
'''




'''
===========================================
research snippets
===========================================
'''


"""

TODO

* run climate scenarios through hydrology model
* do some runs of farmer decision model
* get farmer to use constraints from hydrology including implementing water policy
* update hydrology with results from farmer 

"""


'''
"With the recent volatility in general commodity prices, and the prolonged period of limited water there are no 'typical' rotations in an irrigated farming system. Farmers are choosing crops season by season depending on available water, current commodity prices, pest and disease pressure and various soil health issues."
\cite{powell2011representative}

We need a number of crops, each with a 'name', 'growing season', 'yield (unit/ha)', 'price ($/unit)', 'water use (ML/ha)', 'cost ($/ha)'.

Rather than having a physical model (eg. APSIM) to predict yield we simply include three versions of each crop: irrigated, semi-irrigated, dryland.  


Irrigation vs yield for cotton
--------------------------------

3.2 Managing irrigated cotton agronomy 
http://www.cottoncrc.org.au/industry/Publications/Water/WATERpak/WATERpak_S3_Irrigation_management_of_cotton
CottBASE = {'irrigation' : [0, 2, 4, 6, 8], 'yield' : [1.5, 2.5, 4.5, 7.5, 8.5]}

For fully irrigate cotton, 9 bales/ha not as high as 12 bales/ha from
3.4 Managing irrigation with limited water 
http://www.cottoncrc.org.au/industry/Publications/Water/WATERpak/WATERpak_S3_Irrigation_management_of_cotton
or 
SEMI-IRRIGATED COTTON: MOREE LIMITED WATER EXPERIMENT

Prices
--------------------------------

http://www.theland.com.au/news/agriculture/cropping/cotton/cotton-paying-off/2725482.aspx?storypage=0
http://www.imf.org/external/np/res/commod/index.aspx
http://databank.worldbank.org/data/views/variableselection/selectvariables.aspx?source=global-economic-monitor-%28gem%29-commodities#

http://www.imf.org/external/np/fin/ert/GUI/Pages/Report.aspx?CU=%27AUD%27&EX=REP&P=DateRange&Fr=628929792000000000&To=635621472000000000&CF=UnCompressed&CUF=Period&DS=Ascending&DT=Blank

http://www.abs.gov.au/AUSSTATS/abs@.nsf/second+level+view?ReadForm&prodno=7501.0&viewtitle=Value%20of%20Principal%20Agricultural%20Commodities%20Produced,%20Australia,%20Preliminary~1993-94~Previous~04/08/1994&&tabname=Past%20Future%20Issues&prodno=7501.0&issue=1993-94&num=&view=&
CPI
http://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/6401.0Dec%202014?OpenDocument

http://www.indexmundi.com/commodities/?commodity=cotton&months=360

http://www.cottoncrc.org.au/industry/Publications/Water/WATERpak/WATERpak_S3_Irrigation_management_of_cotton

nsw media release
http://www.water.nsw.gov.au/Water-management/Water-availability/Water-allocations/Available-water-determinations
Available Water Determination Order for Various NSW Groundwater Sources (No. 1) 2014

With the exception of the Upper Namoi groundwater Zone 1, all Upper and Lower
Namoi aquifer access licence holders will receive an allocation of 1 megalitre per unit
share of entitlement.
In Zones 5, 11, and 12 of the Upper Namoi groundwater sources, supplementary
water access licence holders will receive an allocation of 0.2 megalitre per unit share
of entitlement.


{ 
'name':,
'season':,
'yield (unit/ha)':,
'price ($/unit)':,
'water use (ML/ha)':,
'cost ($/ha)':,
  }


Note dryland cotton $20/bale less for quality
Growing summer and winter crops not possible

					water cost 	irrigation cost 	TOTAL
groundwater bore 	9.2			57.45   			66.65
river-regulated  	31.75		12.77   			44.52


http://www.dpi.nsw.gov.au/agriculture/farm-business/budgets/summer-crops
http://www.dpi.nsw.gov.au/agriculture/farm-business/budgets/winter-crops



'''


