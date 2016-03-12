import numpy as np
import os 
import datetime 
import csv

# namoimodel10_dss.r takes about 5 min so we implemented in python here

from ConfigLoader import *

dirname = CONFIG.paths["ecological"] if "ecological" in CONFIG.paths else os.path.dirname(__file__)

indices_dir = os.path.join(dirname, 'Inputs/index/')
chosen_indices_dir = os.path.join(dirname, 'curves/')

"""
creates list of flood events, like hydromad eventseq
"""
def eventseq(flow, threshold, min_separation, min_duration):
	events = []

	pre_below = np.empty_like(flow)
	below_count = 0
	for i in range(len(flow)):
		pre_below[i] = below_count
		if flow[i] < threshold:
			below_count += 1
		else: 
			if below_count > 0:
				events.append(i)
			below_count = 0

	post_above = np.empty_like(flow)
	above_count = 0
	for i in reversed(range(len(flow))):
		if flow[i] >= threshold:
			above_count += 1
		else: 
			above_count = 0
		post_above[i] = above_count

	relevent_events = [{"index": e, "duration": post_above[e], "preceding dry": pre_below[e] } for e in events
		if post_above[e] >= min_duration and pre_below[e] >= min_separation]

	return relevent_events

	# print flow
	# print pre_below
	# print post_above
	# print events

"""
loads columns of a csv
"""

def read_csv_cols(file_name, col_names):
	with open(file_name) as csvfile:
		reader = csv.DictReader(csvfile)
		
		rows = [row for row in reader]
		return tuple([[row[col_name] for row in rows] for col_name in col_names])

		# table = [[row[col_name] for col_name in col_names] for row in reader]
		# return map(list, zip(*table))

def read_csv_cols_remove_blanks(file_name, col_names):
	with open(file_name) as csvfile:
		reader = csv.DictReader(csvfile)
		rows = [row for row in reader if not row[col_names[1]] == '']
		# would be fine if rows were in order
		# return tuple([np.array([row[col_name] for row in rows], dtype=np.float) for col_name in col_names])
		x, y = tuple([np.array([row[col_name] for row in rows], dtype=np.float) for col_name in col_names])
		zippped = zip(x, y)
		zippped.sort(key=lambda d: d[0])
		return tuple([list(t) for t in zip(*zippped)])


"""
creates daily values from a list of events for computing indices
"""

def daily_values_from_events(flood_events, dates):
	timing_values = np.zeros((len(dates)))
	duration_values = np.zeros((len(dates)))
	dry_values = np.zeros((len(dates)))

	for event in flood_events:
		for day in range(int(event["duration"])):
			i = event["index"]+day
			timing_values[i] = datetime.datetime.strptime(dates[i], "%Y-%m-%d").month
			duration_values[i] = event["duration"]
			dry_values[i] = event["preceding dry"]

	return timing_values, duration_values, dry_values

"""
loads index curves and calculates water index
"""

eco_weights_parameters = {
  "Default": {
    "Duration":0.5,
    "Timing":0.2,
    "Dry":0.3
  },
  "Favour duration": {
    "Duration":0.9,
    "Timing":0.05,
    "Dry":0.05
  },
  "Favour dry": {
    "Duration":0.4,
    "Timing":0.1,
    "Dry":0.5
  },
  "Favour timing": {
    "Duration":0.3,
    "Timing":0.5,
    "Dry":0.2
  },
  # "Minimum": {
  #   "Duration":null,
  #   "Timing":null,
  #   "Dry":null
  # }
}

eco_ctf_parameters = { "min": 110, "med": 300, "max": 800 }
eco_min_separation_parameters = { "min": 1, "med": 2, "max": 5 } #if two events are <= 5 days apart, they are combined and considered one event
eco_min_duration_parameters = { "min": 1, "med": 3, "max": 5 } #min number of days that can call an 'event'

def calculate_water_index(gw_level, flow, dates, 
	threshold = 300, 
	min_separation = 2,
	min_duration = 3,
	duration_weight = 0.5,
	timing_weight = 0.2,
	dry_weight = 0.3,
	surface_weight = 0.5,
	gwlevel_weight = 0.5,
	timing_col = 'Roberts',
	duration_col = 'Namoi',
	dry_col = 'Namoi',
	gwlevel_col = 'Index'
	):



	"""
	parameters
	"""
	# # parameters for flood events
	# threshold = 300 #110, 500, 1000 from fu2013water
	# min_separation = 2 # min preceding dry period
	# min_duration = 3
	# # weights
	# duration_weight = 0.5
	# timing_weight = 0.2
	# dry_weight = 0.3

	# surface_weight = 0.5
	# gwlevel_weight = 0.5

	assert duration_weight + timing_weight + dry_weight == 1
	assert surface_weight + gwlevel_weight == 1

	"""
	load index curves
	"""
	species = 'RRGMS'

	# timing_x, timing_y = read_csv_cols(indices_dir + species + '_timing.csv', ['Month','Index'])
	# duration_x, duration_y = read_csv_cols(indices_dir + species + '_duration.csv', ['Days','Index'])
	# dry_x, dry_y = read_csv_cols(indices_dir + species + '_dry.csv', ['Days','Index'])
	# gwlevel_x, gwlevel_y = read_csv_cols(indices_dir + species + '_gwlevel.csv', ['Level_m','Index'])


	timing_x, timing_y = read_csv_cols_remove_blanks(chosen_indices_dir + 'timing_curves.csv', ['Month', timing_col])
	duration_x, duration_y = read_csv_cols_remove_blanks(chosen_indices_dir + 'duration_curves.csv', ['Days', duration_col])
	dry_x, dry_y = read_csv_cols_remove_blanks(chosen_indices_dir + 'dry_curves.csv', ['Days', dry_col])
	gwlevel_x, gwlevel_y = read_csv_cols_remove_blanks(chosen_indices_dir + 'gwlevel_curves.csv', ['Level_m', gwlevel_col])

	"""
	following Section 4.5 from fu2013water
	"""
	flood_events = eventseq(flow, threshold, min_separation, min_duration)

	timing_values, duration_values, dry_values = daily_values_from_events(flood_events, dates)


	duration_index = np.interp(duration_values, duration_x, duration_y)
	timing_index = np.interp(timing_values, timing_x, timing_y)
	dry_index = np.interp(dry_values, dry_x, dry_y)

	surface_index = duration_weight * duration_index + timing_weight * timing_index + dry_weight * dry_index
	gwlevel_index = np.interp(gw_level, gwlevel_x, gwlevel_y)


	# water_index = surface_weight * surface_index + gwlevel_weight * gwlevel_index

	return surface_index, gwlevel_index	


	# print gwlevel_x, gwlevel_y
	# print gw_level

	# print duration_index
	# print dry_index
	# print timing_values
	# print timing_index
	# print timing_x, timing_y
	# gwlevel_index = np.interp(gwlevel_values, gwlevel_x, gwlevel_y)

	# print timing_x, timing_y
	# print gwlevel_x, gwlevel_y
	# print duration_x, duration_y

	# x = [1,1.5,2,3,8,7,9,12]
	# print np.interp(x, xp=timing_x, fp=timing_y, left=None, right=None)

if __name__ == '__main__':
	assert [{'duration': 2, 'index': 2, 'preceding dry': 2}, {'duration': 4, 'index': 7, 'preceding dry': 3}] == eventseq(flow = np.array([1,2,5,6,2,3,3,7,7,8,9,0]),
					threshold = 4.0, 
					min_separation = 0, 
					min_duration = 2)
	
	# demo data
	gw_level = -np.array([-5.312367848826449,-5.296229650632848,-5.273041893321809,-5.255808501097833,-5.243871008740949,-5.235486066118643,-5.2295203061227955,-5.225233782372305,-5.2221401343241824,-5.219426083035854,-5.217255150661642,-5.215765766038076,-5.205921106097377,-5.198153429683988,-5.190284597641773,-5.184820245136232,-5.180143737613151,-5.171861801700441,-5.158047921500803,-5.147737062008881,-5.140411655918827,-5.135149764612964,-5.1313478896890645,-5.128607238606024,-5.12660476978373,-5.124991504713292,-5.1238896014146365,-5.123246592839388,-5.122972785898297,-5.123001981459293,-5.123283737700673,-5.123778417047467,-5.12445400167466,-5.1252840291766875,-5.126029728749374,-5.126929544642842,-5.127803592804486,-5.128822657211075,-5.129955707342943,-5.129784669845781,-5.129920858283373,-5.121161069600153,-5.114622266298915,-5.10962603387095,-5.105721772132054,-5.102653869424742,-5.100244211179446,-5.098374457271736,-5.096962292404344,-5.095947070554314,-5.0952812761582,-5.094925542750818,-5.094845813268083,-5.095011763485012,-5.09539595026035,-5.095973360094781,-5.09672116666361,-5.096852679717054,-5.097062561419894,-5.0973917012570045,-5.097841551266534,-5.098412218259556,-5.099101758259215,-5.099906168030834,-5.10081970659783,-5.101835337479736,-5.102945178559243,-5.1041409038759475,-5.105414074892753,-5.106756397196499,-5.1081599080590765,-5.109617104482519,-5.111009213698404,-5.11237076916877,-5.113516299819644,-5.114534250664001,-5.115261991828128,-5.115261249568658,-5.114796581375864,-5.1140974274425375,-5.113317826722798,-5.112540737349297,-5.111850604532405,-5.111300642618021,-5.110914788064687,-5.110711761261707,-5.110691961178249,-5.11040980057481,-5.1097648598833505,-5.108952420101298,-5.108115955596128,-5.107352219154662,-5.106723466712061,-5.106266785347572,-5.106001173037234,-5.105932878733597,-5.106059400840383,-5.106372454998262,-5.106860153462003,-5.107508584380363,-5.1083029369258695,-5.109228285028569,-5.1102681375948675,-5.111402865236187,-5.112202749788136,-5.111642452436026,-5.110239668453143,-5.1083804371243495,-5.1063374209381855,-5.104299317307518,-5.102392306921646,-5.100696496868292,-5.09925846431461,-5.098102750426593,-5.0972363276968755,-5.096654159593748,-5.096343323291823,-5.0962860332591,-5.096461828400693,-5.096849126445776,-5.097426302975691,-5.0981084312529035,-5.09877874733379,-5.099478969308561,-5.100234885143144,-5.101062410288876,-5.1019709775268876,-5.1029627218270965,-5.104037459892027,-5.105192137353801,-5.106421876362564,-5.1076976503469425,-5.1088492876216876,-5.1098094010191435,-5.1105017541752416,-5.111026563339682,-5.111480468998444,-5.11193169982774,-5.112414000993156,-5.112958703230161,-5.113545972601941,-5.114182819732801,-5.114889657501309,-5.115677012495827,-5.116551079923337,-5.1175116437174735,-5.118551893762335,-5.11916017041607,-5.118600257687881,-5.11714035265184,-5.1151853975084665,-5.112613397295755,-5.109879665701296,-5.1071875957311,-5.104674368286121,-5.102394869176993,-5.100400648520592,-5.0984836136738805,-5.096809595685725,-5.095414119280549,-5.094165553439942,-5.093128362220902,-5.092332322239644,-5.091786083932234,-5.091486598735392,-5.091423817965736,-5.091581243283726,-5.091942488996678,-5.0924897516486,-5.093204832621687,-5.093781914601954,-5.0936445813840505,-5.09309665509003,-5.092454277025708,-5.091824322871392,-5.09128366921369,-5.090880335845185,-5.09064282849545,-5.090585274782631,-5.090711464627082,-5.091017980154642,-5.091496584065931,-5.092136013929201,-5.092923307181353,-5.093844760099175,-5.09457195307248,-5.095206668525628,-5.095819972239738,-5.0964586849902975,-5.0971544775889,-5.097926499574514,-5.09878487727274,-5.099733355601254,-5.100771278932435,-5.101881541105593,-5.102993411202846,-5.103971398056659,-5.104851778122502,-5.105697942974325,-5.106553304065166,-5.107446454006666,-5.107605881813213,-5.1070097295233,-5.105959111699932,-5.1047998899922575,-5.1036589127515795,-5.102626813966728,-5.101758352014688,-5.101086853925947,-5.1006303535442985,-5.100393396340392,-5.1003718960255755,-5.100556014777398,-5.100932317705455,-5.101485357974745,-5.102198820321317,-5.103056325824274,-5.1040390114240966,-5.1051329084746575,-5.106307984363964,-5.10755812175387,-5.1088765552211335,-5.110254987204794,-5.1116870085891986,-5.112218260811675,-5.112236361275614,-5.111938325317221,-5.111502472986702,-5.111048839500511,-5.110658341120078,-5.110383099279488,-5.110254165147752,-5.110283781481315,-5.110390694035713,-5.110600806595599,-5.110836233778408,-5.110985696487825,-5.11112551958184,-5.111193878349748,-5.111148590440985,-5.111085717929916,-5.111073335481491,-5.111155211077391,-5.111350785256728,-5.111565938459637,-5.111761845467627,-5.1118508640944444,-5.111791250343462,-5.11142831940838,-5.109339344117919,-5.106960715286956,-5.103445707644083,-5.100177027495825,-5.097224116881669,-5.094618926545502,-5.092379945613973,-5.090501828442179,-5.0889820612904115,-5.08781747922943,-5.0869852695391975,-5.086466371628659,-5.08623575362078,-5.08626746481815,-5.0865356135004225,-5.086952981493086,-5.087198816958318,-5.087448742086609,-5.087815921729205,-5.088306156687154,-5.088921024939393,-5.089658548764369,-5.090513992228298,-5.091365214215606,-5.0922378156683115,-5.0929804222689565,-5.093709105539032,-5.094464320962544,-5.0952726458953475,-5.096150294985986,-5.0971012645598694,-5.097813773990289,-5.09829806462325,-5.098586177690887,-5.098794934905485,-5.098735140989435,-5.098447780017968,-5.097897616241868,-5.097118788879215,-5.094196260094119,-5.085086794001415,-5.073235784333511,-5.061254244477075,-5.05120390596284,-5.042648081163103,-5.035325914962729,-5.029092857465724,-5.0238228909066,-5.019409580721861,-5.015763390219389,-5.012748267702002,-5.010198507539953,-5.007485298450585,-4.999715545034022,-4.9932502551054645,-4.98815783378877,-4.983889708195141,-4.9805219292280665,-4.977893269240529,-4.975889015558564,-4.974092886596223,-4.9711021887035844,-4.9687394779587795,-4.967016664096012,-4.965820198084255,-4.964730067974379,-4.959336801760003,-4.952275134345854,-4.9372184190343305,-4.925155234767944,-4.911520270131662,-4.898578233932342,-4.888380544219807,-4.880119764141575,-4.873508007285509,-4.868181132480875,-4.863829963483894,-4.860418889807529,-4.857808735835618,-4.855890394623887,-4.854574756284282,-4.853786596983802,-4.853460874204294,-4.853540462973876,-4.8539747404243165,-4.8547186600414864,-4.855725725122333,-4.856967558383702,-4.858412229419045,-4.86003157483297,-4.861800812778753,-4.863639122997864,-4.865587752293887,-4.867630611254061,-4.8697539255236855,-4.871768538330647,-4.872019429147781,-4.87114592483275,-4.870346594859308,-4.8697312687823855,-4.869316302248988,-4.869116488007106,-4.869141374971938,-4.869394258774339,-4.869867549363132,-4.870289017068627,-4.870394362998957,-4.868457965563208,-4.865661784247512,-4.862656384761755,-4.859641460986985,-4.857105236709082,-4.855024236692115,-4.853381139008032,-4.85215234340111,-4.85132439475272])
	flow = np.array([2221.4080365990385, 2574.7214726657326, 3575.81778991691, 2549.7298483919953, 1667.7523803795052, 1091.3393316849133, 714.6305892121314, 468.43908351300104, 307.546292109898, 277.2962170790433, 222.2362522698288, 146.67787909600992, 1447.5971373740092, 1101.8582073965083, 1102.345215392258, 722.3788976011639, 605.5131867206131, 1158.6951938711109, 1976.4258950670383, 1387.8551161862533, 909.5877724367488, 597.0237443249074, 392.7544259233772, 259.2594093082097, 180.37011456394217, 156.00107448057068, 112.12445851266345, 75.86576405646588, 52.162789331753515, 36.66360182950996, 26.524169950080463, 19.885963028868375, 15.534524226462665, 12.676323241371806, 41.54981833929009, 31.226334513013583, 45.261310844965344, 32.05544590973596, 23.407377240023553, 206.43387043729865, 143.35338417868817, 1370.2906567748887, 900.0937409957271, 591.1362326186497, 391.4250092655413, 258.7276935216983, 172.0154689338294, 115.35372269205587, 78.32824501232172, 54.132867032105366, 38.31956657394545, 27.981552268155973, 21.219336248518854, 16.791764816813167, 13.88793585806265, 11.978126950882984, 10.716364461234857, 86.75619677911905, 63.77299466659062, 44.56947287699175, 32.01002101718718, 23.79140127381434, 18.408359258594654, 14.877205292751054, 12.555143326749963, 11.022181161722688, 10.003944570165908, 9.32122693946621, 8.85701389523272, 8.534930097674517, 8.30515198002791, 8.13520053081969, 8.008019157580971, 7.908352049902162, 7.833848471618025, 7.7752926198487735, 7.734735281606941, 7.725676497216584, 7.7367577739254125, 7.758484869733396, 7.784503056025627, 7.8113080044819165, 7.835502280857381, 7.854937818401174, 7.868607850379995, 7.875741709542634, 7.8762692372814165, 7.886474843639901, 7.910012912286481, 7.93971529636595, 7.970316764490604, 7.9982668874442915, 8.02128106152811, 8.037998053151966, 8.047720166172764, 8.0502173089624, 8.045580318649082, 8.034112113721681, 8.016247774259186, 7.992496635018909, 7.963401034336713, 7.929507581513159, 7.891420241268613, 7.849857947307861, 7.820560142854384, 9.766606145477557, 9.518526789036299, 9.02330893284102, 8.729972203637418, 8.56399952439675, 8.47658421497483, 8.435914144999986, 8.421409496477487, 8.419836021286352, 8.422876302834826, 8.425445710418083, 8.424573841997374, 8.418661414465179, 8.406986860095476, 8.389379276541389, 8.36600236445195, 8.339556103034566, 8.314048854036356, 8.287777172471898, 8.259681863030732, 8.229105052829713, 8.195652270760883, 8.159213311335332, 8.11977396938557, 8.077432446596978, 8.032358470461471, 7.985609369494403, 7.9434142773272765, 7.908238917755601, 7.8828740020333035, 7.86364780147622, 7.847019927589508, 7.830490884519726, 7.812824376296342, 7.792872644354419, 7.771362027641744, 7.748035661985965, 7.7221458219600105, 7.693306910256991, 7.661291989220513, 7.626108957661562, 7.588007242670974, 7.56572761255632, 7.586235758555094, 7.84225520721923, 7.843691939462096, 26.11092033284348, 20.47615592490905, 16.45071435810692, 13.616663205652813, 12.986982943663723, 11.83207375183861, 21.317078065863427, 16.876879871623814, 13.985936646427394, 18.39371624855802, 16.387972551138077, 13.832190647770307, 12.021723698795743, 10.836349210815197, 10.05675372774122, 9.539964198126563, 9.192742880548842, 8.954412187617738, 8.785555420575026, 8.671176641372387, 42.04503334280845, 48.16243346680024, 34.81150245229969, 26.03894655274177, 20.005939872894174, 16.064775620434396, 13.487991216651038, 11.800303553900235, 10.691281023428296, 9.95825061584459, 9.468971135425008, 9.137228970305934, 8.906882630791907, 8.741431325283315, 8.62931220817704, 8.549602582068944, 8.490237191879153, 8.442724958237724, 8.401477166300559, 8.362897953932864, 8.324724683898125, 8.285583806772152, 8.244691273299157, 8.20214551185989, 8.160192046104575, 8.123567977119764, 8.09079715190405, 8.059461338038394, 8.027907506245414, 7.995047221217582, 16.996972303881016, 40.88242173505372, 46.477368845459914, 33.20719122412083, 24.773247858685234, 19.046549980741418, 15.463896606831181, 13.083713963198875, 11.41816989579909, 10.327370680243803, 9.609571635444063, 9.133180915740496, 8.812450562556627, 8.591582410278562, 8.434336237792206, 8.317235860965022, 8.225236756658518, 8.148566349532747, 8.081603200618343, 8.020178427160907, 7.961668730154895, 7.904501562431725, 7.847685271019505, 15.393912269387052, 12.769419363259066, 11.973925795970827, 10.581111247859651, 9.650275792576483, 9.045352854224982, 8.650726518502104, 8.390944031490784, 8.21698660464836, 8.100086215001708, 8.018547031250048, 7.961662140733564, 7.924645221384223, 7.8989086256561665, 7.882931311264311, 7.875784203664713, 7.872331794335114, 7.869023858843577, 7.863566579303066, 7.85479647156303, 7.845865853145873, 7.838003962687811, 7.8342948803278265, 7.836185213341569, 10.892009267475338, 158.96626751322594, 127.68492631398655, 227.32405955323688, 154.20459470600113, 103.75358753187389, 70.80503350206068, 49.29047608167828, 36.50458491586505, 27.952036903571617, 21.315197015819585, 17.37357532158722, 14.403114428001462, 12.457734251905125, 11.17960910469762, 10.335201817727018, 14.532837939688992, 42.18722040395647, 41.29796558804141, 30.001053010095895, 22.60855862429497, 17.766257324742238, 14.589177828368554, 12.499055186651264, 14.598761826302233, 13.276896758836982, 17.578799736427342, 14.415475924628897, 12.33780305615116, 10.968369429072016, 10.060552235731057, 9.45340788044692, 9.053263774522874, 8.791075739607711, 8.624072583080025, 8.51084408736963, 11.150068758285496, 14.449802209939543, 22.373692360537596, 29.36072724932825, 243.43521142438794, 987.0735292107074, 1209.1616360851478, 1084.0240673490848, 717.1078721807936, 479.4565842981998, 323.449781430031, 216.68816570008596, 145.57784464533702, 99.13773347317989, 69.09429281953678, 57.491024173494, 64.06365839183124, 145.81404407277182, 877.8364427689175, 636.8713906328456, 421.32970310942915, 312.37747189717714, 208.6214489796589, 140.8252406914763, 96.5261273054723, 110.93943546977653, 305.2133674928105, 222.60210229372254, 150.0789090336162, 102.6824755138116, 115.00656777833497, 710.542296087267, 873.54737644313, 1941.1116344557456, 1348.0621502504018, 1492.8823112656676, 1316.820320795893, 874.2229961561203, 599.2650086120782, 397.5581991585496, 269.75736510721026, 197.89747642422213, 135.3257106854608, 94.44460118559948, 67.7336969772913, 50.27850563383715, 38.86768227318038, 31.402968398547678, 26.513539597392697, 23.303952250382462, 21.189408975524056, 20.59658964252465, 19.37950157988314, 18.560861973813644, 18.001094280412126, 17.60920889955857, 23.605649340539514, 21.21983422727717, 19.63235879591647, 18.565963436316412, 30.463815545631974, 206.1572854047793, 275.0857508150961, 196.03612496037547, 133.92409698024798, 93.32998071567854, 66.79625130346388, 49.44889531286741, 38.102509525065074, 31.000440067319822, 41.541044274086886, 66.00295270189841, 277.67612653357037, 315.9776547639807, 282.95051972223195, 246.1327918488881, 166.87199063190076, 115.08498201840521, 81.2488902865835, 59.820169155112595, 45.13602643494705])
	dates = ['1969-01-01','1969-01-02','1969-01-03','1969-01-04','1969-01-05','1969-01-06','1969-01-07','1969-01-08','1969-01-09','1969-01-10','1969-01-11','1969-01-12','1969-01-13','1969-01-14','1969-01-15','1969-01-16','1969-01-17','1969-01-18','1969-01-19','1969-01-20','1969-01-21','1969-01-22','1969-01-23','1969-01-24','1969-01-25','1969-01-26','1969-01-27','1969-01-28','1969-01-29','1969-01-30','1969-01-31','1969-02-01','1969-02-02','1969-02-03','1969-02-04','1969-02-05','1969-02-06','1969-02-07','1969-02-08','1969-02-09','1969-02-10','1969-02-11','1969-02-12','1969-02-13','1969-02-14','1969-02-15','1969-02-16','1969-02-17','1969-02-18','1969-02-19','1969-02-20','1969-02-21','1969-02-22','1969-02-23','1969-02-24','1969-02-25','1969-02-26','1969-02-27','1969-02-28','1969-03-01','1969-03-02','1969-03-03','1969-03-04','1969-03-05','1969-03-06','1969-03-07','1969-03-08','1969-03-09','1969-03-10','1969-03-11','1969-03-12','1969-03-13','1969-03-14','1969-03-15','1969-03-16','1969-03-17','1969-03-18','1969-03-19','1969-03-20','1969-03-21','1969-03-22','1969-03-23','1969-03-24','1969-03-25','1969-03-26','1969-03-27','1969-03-28','1969-03-29','1969-03-30','1969-03-31','1969-04-01','1969-04-02','1969-04-03','1969-04-04','1969-04-05','1969-04-06','1969-04-07','1969-04-08','1969-04-09','1969-04-10','1969-04-11','1969-04-12','1969-04-13','1969-04-14','1969-04-15','1969-04-16','1969-04-17','1969-04-18','1969-04-19','1969-04-20','1969-04-21','1969-04-22','1969-04-23','1969-04-24','1969-04-25','1969-04-26','1969-04-27','1969-04-28','1969-04-29','1969-04-30','1969-05-01','1969-05-02','1969-05-03','1969-05-04','1969-05-05','1969-05-06','1969-05-07','1969-05-08','1969-05-09','1969-05-10','1969-05-11','1969-05-12','1969-05-13','1969-05-14','1969-05-15','1969-05-16','1969-05-17','1969-05-18','1969-05-19','1969-05-20','1969-05-21','1969-05-22','1969-05-23','1969-05-24','1969-05-25','1969-05-26','1969-05-27','1969-05-28','1969-05-29','1969-05-30','1969-05-31','1969-06-01','1969-06-02','1969-06-03','1969-06-04','1969-06-05','1969-06-06','1969-06-07','1969-06-08','1969-06-09','1969-06-10','1969-06-11','1969-06-12','1969-06-13','1969-06-14','1969-06-15','1969-06-16','1969-06-17','1969-06-18','1969-06-19','1969-06-20','1969-06-21','1969-06-22','1969-06-23','1969-06-24','1969-06-25','1969-06-26','1969-06-27','1969-06-28','1969-06-29','1969-06-30','1969-07-01','1969-07-02','1969-07-03','1969-07-04','1969-07-05','1969-07-06','1969-07-07','1969-07-08','1969-07-09','1969-07-10','1969-07-11','1969-07-12','1969-07-13','1969-07-14','1969-07-15','1969-07-16','1969-07-17','1969-07-18','1969-07-19','1969-07-20','1969-07-21','1969-07-22','1969-07-23','1969-07-24','1969-07-25','1969-07-26','1969-07-27','1969-07-28','1969-07-29','1969-07-30','1969-07-31','1969-08-01','1969-08-02','1969-08-03','1969-08-04','1969-08-05','1969-08-06','1969-08-07','1969-08-08','1969-08-09','1969-08-10','1969-08-11','1969-08-12','1969-08-13','1969-08-14','1969-08-15','1969-08-16','1969-08-17','1969-08-18','1969-08-19','1969-08-20','1969-08-21','1969-08-22','1969-08-23','1969-08-24','1969-08-25','1969-08-26','1969-08-27','1969-08-28','1969-08-29','1969-08-30','1969-08-31','1969-09-01','1969-09-02','1969-09-03','1969-09-04','1969-09-05','1969-09-06','1969-09-07','1969-09-08','1969-09-09','1969-09-10','1969-09-11','1969-09-12','1969-09-13','1969-09-14','1969-09-15','1969-09-16','1969-09-17','1969-09-18','1969-09-19','1969-09-20','1969-09-21','1969-09-22','1969-09-23','1969-09-24','1969-09-25','1969-09-26','1969-09-27','1969-09-28','1969-09-29','1969-09-30','1969-10-01','1969-10-02','1969-10-03','1969-10-04','1969-10-05','1969-10-06','1969-10-07','1969-10-08','1969-10-09','1969-10-10','1969-10-11','1969-10-12','1969-10-13','1969-10-14','1969-10-15','1969-10-16','1969-10-17','1969-10-18','1969-10-19','1969-10-20','1969-10-21','1969-10-22','1969-10-23','1969-10-24','1969-10-25','1969-10-26','1969-10-27','1969-10-28','1969-10-29','1969-10-30','1969-10-31','1969-11-01','1969-11-02','1969-11-03','1969-11-04','1969-11-05','1969-11-06','1969-11-07','1969-11-08','1969-11-09','1969-11-10','1969-11-11','1969-11-12','1969-11-13','1969-11-14','1969-11-15','1969-11-16','1969-11-17','1969-11-18','1969-11-19','1969-11-20','1969-11-21','1969-11-22','1969-11-23','1969-11-24','1969-11-25','1969-11-26','1969-11-27','1969-11-28','1969-11-29','1969-11-30','1969-12-01','1969-12-02','1969-12-03','1969-12-04','1969-12-05','1969-12-06','1969-12-07','1969-12-08','1969-12-09','1969-12-10','1969-12-11','1969-12-12','1969-12-13','1969-12-14','1969-12-15','1969-12-16','1969-12-17','1969-12-18','1969-12-19','1969-12-20','1969-12-21','1969-12-22','1969-12-23','1969-12-24','1969-12-25','1969-12-26','1969-12-27','1969-12-28','1969-12-29','1969-12-30','1969-12-31']

	water_index = calculate_water_index(gw_level, flow, dates)
	# print water_index

	


