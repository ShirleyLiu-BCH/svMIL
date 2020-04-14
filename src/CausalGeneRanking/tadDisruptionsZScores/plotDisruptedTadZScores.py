"""
	Instead of plotting each TAD individually, plot the pairs of TADs that are disrupted by an SV. Make sure to split this across SV types. 

"""
import sys

path = sys.argv[2]
sys.path.insert(1, path)

import settings
#this code depends on the input parser from the linking part. This is quick and dirty, is there a better solution?
sys.path.insert(1, 'linkSVsGenes/')

import sys
import numpy as np
import settings
from inputParser import InputParser
from statsmodels.sandbox.stats.multicomp import multipletests
from scipy import stats
import matplotlib.pyplot as plt
import glob
import ast
from genomicShuffler import GenomicShuffler

import matplotlib
#matplotlib.use('Agg')

bins = 10

def getBinScores(zScores, rules, cosmicRules, expressionCutoff, randomExpression, svType):

	splitZScores = []
	allPatients = []
	for zScore in zScores:
		splitScore = zScore[0].split("_")

		#if zScore[3] != 'False': #only look at the ones which we actually mapped.
		splitZScores.append([splitScore[0], splitScore[1], float(zScore[5])])

		if splitScore[0] not in allPatients:
			allPatients.append(splitScore[0])

	zScores = np.array(splitZScores, dtype='object')

	causalGenes = InputParser().readCausalGeneFile(settings.files['causalGenesFile'])
	nonCausalGenes = InputParser().readNonCausalGeneFile(settings.files['nonCausalGenesFile'], causalGenes) #In the same format as the causal genes.

	#Combine the genes into one set.
	allGenes = np.concatenate((causalGenes, nonCausalGenes), axis=0)
	if cosmicRules == 'True':
		allGenes = causalGenes

	causalGeneList = []
	for gene in causalGenes:
		causalGeneList.append(gene[3].name)
	#then go through the TADs that are disrupted by a non-coding SV.

	#Get all SVs
	svDir = settings.files['svDir']
	svData = InputParser().getSVsFromFile_hmf(svDir)

	filteredSVs = []
	types = []
	for sv in svData:

		if svType != 'ALL':
			if sv[8].svType != svType:
				continue

		svEntry = sv[0] + "_" + str(sv[1]) + "_" + str(sv[2]) + "_" + sv[3] + "_" + str(sv[4]) + "_" + str(sv[5]) + "_" + sv[8].sampleName
		#if svEntry not in excludedSVs:
		#	filteredSVs.append(sv)
		filteredSVs.append(sv)
		if sv[8].svType not in types:
			types.append(sv[8].svType)

	print(types)
	filteredSVs = np.array(filteredSVs, dtype='object')

	#np.save('filteredSVs_tadPairs_' + svType + '.npy', filteredSVs)
	#filteredSVs = np.load('filteredSVs_tadPairs_' + svType + '.npy', allow_pickle=True, encoding='latin1')

	#For each SV, determine which TAD it starts and ends in.
	#Keep this as a TAD pair.
	tadFile = settings.files['tadFile']
	tadData = InputParser().getTADsFromFile(tadFile)

	tadPairs = dict() #keep the pair as name, and the patients as value.
	for sv in filteredSVs:

		#get the left and rightmost TAD.

		#if intrachromosomal, check overlap
		if sv[0] == sv[3]:
			tadChrSubsetInd = sv[0] == tadData[:,0]
			tadChrSubset = tadData[tadChrSubsetInd]

			#If the SV start is before the end of the TAD, and the SV end after the start of the TAD, the TAD is overlapped.
			startMatches = sv[1] <= tadChrSubset[:,2]
			endMatches = sv[5] >= tadChrSubset[:,1]

			tadMatches = tadChrSubset[startMatches * endMatches]

			if tadMatches.shape[0] < 2: #no matches, or overlapping just 1 TAD.
				continue

			#Get the leftmost and rightmost TADs
			farLeftTad = tadMatches[0] #This list is sorted
			farRightTad = tadMatches[tadMatches.shape[0]-1]


			tadPair = farLeftTad[0] + '_' + str(farLeftTad[1]) + '_' + str(farLeftTad[2]) + '_' + farRightTad[0] + '_' + str(farRightTad[1]) + '_' + str(farRightTad[2])

			if tadPair not in tadPairs:
				tadPairs[tadPair] = []
			tadPairs[tadPair].append(sv[7])



		else: #if interchromosomal, determine the TAD based on breakpoints on either chromosome.

			tadChr1SubsetInd = sv[0] == tadData[:,0]
			tadChr1Subset = tadData[tadChr1SubsetInd]

			#If the SV start is before the end of the TAD, and the SV end after the start of the TAD, the TAD is overlapped.
			startMatches = sv[1] <= tadChr1Subset[:,2]
			endMatches = sv[5] >= tadChr1Subset[:,1]

			tadMatches = tadChr1Subset[startMatches * endMatches]

			if tadMatches.shape[0] < 1: #no matches
				continue

			#Get the leftmost and rightmost TADs
			farLeftTad = tadMatches[0] #This list is sorted

			#repeat for right TAD
			tadChr2SubsetInd = sv[0] == tadData[:,0]
			tadChr2Subset = tadData[tadChr2SubsetInd]

			#If the SV start is before the end of the TAD, and the SV end after the start of the TAD, the TAD is overlapped.
			startMatches = sv[1] <= tadChr2Subset[:,2]
			endMatches = sv[5] >= tadChr2Subset[:,1]

			tadMatches = tadChr2Subset[startMatches * endMatches]

			if tadMatches.shape[0] < 1: #no matches
				continue

			farRightTad = tadMatches[0]

			tadPair = farLeftTad[0] + '_' + str(farLeftTad[1]) + '_' + str(farLeftTad[2]) + '_' + farRightTad[0] + '_' + str(farRightTad[1]) + '_' + str(farRightTad[2])

			if tadPair not in tadPairs:
				tadPairs[tadPair] = []
			tadPairs[tadPair].append(sv[7])

	#have an additional filter here for the TADs; if there is one TAD pair where we also see the same TAD boundary disrupted again in the same patient, but on another side, we should ignore it for now.

	#if the start of the left TAD is also the end of another pair, or te end of the right TAD is the start of another pair, then we should remove this pair.
	#how often does this happen?
	splitPairs = []
	for pair in tadPairs:
		splitPair = pair.split('_')
		splitPairs.append([splitPair[0], int(splitPair[1]), int(splitPair[2]), splitPair[3], int(splitPair[4]), int(splitPair[5])])

	splitPairs = np.array(splitPairs, dtype='object')


	tadPairsFiltered = dict()
	for pair in splitPairs:

		pairChrSubset = splitPairs[splitPairs[:,3] == pair[0]]
		pairStr = '_'.join([str(i) for i in pair])

		pairPatients = tadPairs[pairStr]

		matched = False

		if pair[1] in pairChrSubset[:,5]:
			matchingPairs = pairChrSubset[pairChrSubset[:,5] == pair[1]]

			#for these matches, check if they are also disrupted in the same patient.
			for matchedPair in matchingPairs:
				matchedPairStr = '_'.join([str(i) for i in matchedPair])

				matchedPairPatients = tadPairs[matchedPairStr]

				for patient in matchedPairPatients:
					if patient in pairPatients:
						#print(pair, ' has match in : ', matchedPairStr, ' patient: ', patient)
						matched = True

		if pair[5] in pairChrSubset[:,1]:
			matchingPairs = pairChrSubset[pairChrSubset[:,1] == pair[5]]
			#for these matches, check if they are also disrupted in the same patient.
			for matchedPair in matchingPairs:
				matchedPairStr = '_'.join([str(i) for i in matchedPair])

				matchedPairPatients = tadPairs[matchedPairStr]

				for patient in matchedPairPatients:
					if patient in pairPatients:
						matched = True
						#print(pairStr, ' has match in : ', matchedPairStr, ' patient: ', patient)


		windowOverlap = False

		if matched == False and windowOverlap == False:
			if pairStr not in tadPairsFiltered:
				tadPairsFiltered[pairStr] = pairPatients

	#np.save('tadPairsFiltered_' + svType + '.npy', tadPairsFiltered)
	#tadPairsFiltered = np.load('tadPairsFiltered_' + svType + '.npy', allow_pickle=True, encoding='latin1').item()
	
	#also use a map for the gene names
	geneNameConversionMap = dict()
	geneNameConversionFile = settings.files['geneNameConversionFile']
	with open(geneNameConversionFile, 'r') as inF:

		lineCount = 0
		for line in inF:

			if lineCount < 1:
				lineCount += 1
				continue
			line = line.strip()
			splitLine = line.split("\t")
			ensgId = splitLine[3]
			splitEnsgId = ensgId.split('.') #we only keep everything before the dot
			geneName = splitLine[4]
			geneNameConversionMap[splitEnsgId[0]] = geneName


	if rules == 'True':
		ruleBasedCombinations = np.loadtxt('output/HMF_BRCA/linkedSVGenePairs/nonCoding_geneSVPairs.txt_', dtype='object')
		ruleBasedPairs = []
		ruleBasedPairsSVs = []
		for combination in ruleBasedCombinations:

			splitPair = combination[0].split('_')

			ruleBasedPairs.append(splitPair[0] + '_' + splitPair[7])
			ruleBasedPairsSVs.append(splitPair[0] + '_' + splitPair[7] + '_' + splitPair[12])
	# elif rules == 'True' and randomExpression == 'True':
	# 	ruleBasedCombinations = np.loadtxt('output/HMF_BRCA/linkedSVGenePairs/random/nonCoding_geneSVPairs.txt_0', dtype='object')
	# 	ruleBasedPairs = []
	# 	ruleBasedPairsSVs = []
	# 	for combination in ruleBasedCombinations:
	#
	# 		splitPair = combination[0].split('_')
	# 
	# 		ruleBasedPairs.append(splitPair[0] + '_' + splitPair[7])
	# 		ruleBasedPairsSVs.append(splitPair[0] + '_' + splitPair[7])
	elif cosmicRules == 'True':
		ruleBasedCombinations = np.loadtxt('output/HMF_BRCA/linkedSVGenePairs/cosmic/nonCoding_geneSVPairs.txt_', dtype='object')
		ruleBasedPairs = []
		ruleBasedPairsSVs = []
		for combination in ruleBasedCombinations:
	
			splitPair = combination[0].split('_')
	
			ruleBasedPairs.append(splitPair[0] + '_' + splitPair[7])
			ruleBasedPairsSVs.append(splitPair[0] + '_' + splitPair[7] + '_' + splitPair[12])

	mutDir = 'output/HMF_BRCA/patientGeneMutationPairs/'
	#Collect all patients with mutations, easier in the adjacent TAds to just filter all patienst with ANY mutations witout having to go through all types individually.
	svPatients = np.load(mutDir + 'svPatients.npy', allow_pickle=True, encoding='latin1').item()
	snvPatients = np.load(mutDir + 'snvPatients.npy', allow_pickle=True, encoding='latin1').item()
	cnvPatients = np.load(mutDir + 'cnvPatients.npy', allow_pickle=True, encoding='latin1').item()

	#also keep the separate mutation types to chec per SV type.
	svPatientsDel = np.load(mutDir + 'svPatientsDel.npy', allow_pickle=True, encoding='latin1').item()
	svPatientsDup = np.load(mutDir + 'svPatientsDup.npy', allow_pickle=True, encoding='latin1').item()
	svPatientsInv = np.load(mutDir + 'svPatientsInv.npy', allow_pickle=True, encoding='latin1').item()
	svPatientsItx = np.load(mutDir + 'svPatientsItx.npy', allow_pickle=True, encoding='latin1').item()

	cnvPatientsDel = np.load(mutDir + 'cnvPatientsDel.npy', allow_pickle=True, encoding='latin1').item()
	cnvPatientsAmp = np.load(mutDir + 'cnvPatientsAmp.npy', allow_pickle=True, encoding='latin1').item()



	bins = 10 #have 10 on each side.
	binZScores = dict()

	for binInd in range(0, bins*2):

		if binInd not in binZScores:
			binZScores[binInd] = []


	binZScoresPerPatient = dict()
	for patient in allPatients:
		binZScoresPerPatient[patient] = dict()

		for binInd in range(0, bins*2):
			binZScoresPerPatient[patient][binInd] = []

	perTadPositivePatients = dict()

	for tad in tadPairs:

		perTadPositivePatients[tad] = []

		splitTad = tad.split('_')

		#Make a mapping for positions to the right bin.

		#determine the size and how large each bin should be
		binSizeTad1 = (float(splitTad[2]) - float(splitTad[1])) / bins

		#binSizeTad1 = (float(splitTad[2]) - (float(splitTad[1]) - offset)) / bins

		currentStart = float(splitTad[1]) #start at the TAD start
		#currentStart = float(splitTad[1]) - offset
		binStartsTad1 = [currentStart] #list at which position each bin should start.
		for binInd in range(0, bins):

			currentStart += binSizeTad1
			binStartsTad1.append(currentStart)

		#repeat for TAD 2
		binSizeTad2 = (float(splitTad[5]) - float(splitTad[4])) / bins
		#binSizeTad2 = ((float(splitTad[5]) + offset) - float(splitTad[4])) / bins
		currentStart = float(splitTad[4]) #start at the TAD start
		binStartsTad2 = [currentStart] #list at which position each bin should start.
		for binInd in range(0, bins):

			currentStart += binSizeTad2
			binStartsTad2.append(currentStart)

		#Go through the genes of the first TAD; find the genes that will be in this bin
		geneChrSubset = allGenes[allGenes[:,0] == splitTad[0]]

		for binInd in range(0, len(binStartsTad1)-1):


			#get the genes in this bin
			genes = geneChrSubset[(geneChrSubset[:,2] >= binStartsTad1[binInd]) * (geneChrSubset[:,1] <= binStartsTad1[binInd+1])]

			#get the z-scores of these genes
			allGeneZScores = []
			geneZScoresPerPatient = dict()
			for gene in genes:
				geneName = gene[3].name

				if geneName in zScores[:,1]: #only add the gene if it has a match.

					geneZScores = zScores[zScores[:,1] == geneName]

					#keep the z-scores separate for each patient

					for patient in range(0, len(geneZScores[:,0])):

						if geneZScores[patient,0] not in tadPairs[tad]:
							continue

						if geneZScores[patient,0] not in perTadPositivePatients[tad]:
							perTadPositivePatients[tad].append(geneZScores[patient,0])


						sample = geneZScores[patient,0]

						if rules == 'True' or cosmicRules == 'True':
							if geneName + '_' + sample not in ruleBasedPairs:
								continue

							#check cnv amp

							#if gene[3].name in cnvPatientsAmp[sample] and gene[3].name not in svPatientsDup[sample]:
							if gene[3].name in cnvPatientsAmp[sample] and gene[3].name + '_' + sample + '_DUP' not in ruleBasedPairsSVs:
								continue

						if svType == 'DEL':
							#only for a deletion, we do not need to print the deleted genes.
							#if a gene is deleted, the deletion will never result in the gain effect.
							#this is only true for deletions.

							if gene[3].name in svPatientsDel[sample] or gene[3].name in cnvPatientsDel[sample]:
								continue




						if str(float(geneZScores[patient,2])) == 'nan':
							continue

						finalScore = 0
						if randomExpression == 'True':
							import random
							randInd = random.sample(range(0, zScores.shape[0]), 1)[0]
							finalScore = float(zScores[randInd,2])
						else:
							finalScore = float(geneZScores[patient,2])

						if expressionCutoff == 'True':
							if finalScore < 1.5 and finalScore > -1.5:
								continue
							
						allGeneZScores.append(finalScore)
						print('LT: ', binInd, geneName, geneZScores[patient,0], finalScore)
						# import random
						# randInd = random.sample(range(0, zScores.shape[0]), 1)[0]
						# randomScore = float(zScores[randInd,2])
						# finalScore = float(geneZScores[patient,2])
						#
						# allGeneZScores.append(abs(finalScore - randomScore) * np.sign(finalScore))
						# print('LT: ', binInd, geneName, geneZScores[patient,0], abs(finalScore - randomScore))


			if len(allGeneZScores) > 0:
				binZScores[binInd] += allGeneZScores

		#now for TAD 2, start from where the TAD 1 indices left off.
		geneChrSubset = allGenes[allGenes[:,0] == splitTad[3]]

		for binInd in range(0, len(binStartsTad2)-1):

			#get the genes in this bin
			genes = geneChrSubset[(geneChrSubset[:,2] >= binStartsTad2[binInd]) * (geneChrSubset[:,1] <= binStartsTad2[binInd+1])]

			#get the z-scores of these genes
			allGeneZScores = []
			geneZScoresPerPatient = dict()
			for gene in genes:
				geneName = gene[3].name



				if geneName in zScores[:,1]:

					geneZScores = zScores[zScores[:,1] == geneName]

					#keep the z-scores separate for each patient
					for patient in range(0, len(geneZScores[:,0])):

						if geneZScores[patient,0] not in tadPairs[tad]:
							continue
						
						if geneZScores[patient,0] not in perTadPositivePatients[tad]:
							perTadPositivePatients[tad].append(geneZScores[patient,0])
						

					
						sample = geneZScores[patient,0]
						
						if rules == 'True' or cosmicRules == 'True':
							if geneName + '_' + sample not in ruleBasedPairs:
								continue

							if gene[3].name in cnvPatientsAmp[sample] and gene[3].name + '_' + sample + '_DUP' not in ruleBasedPairsSVs:
								continue
						#do the check per SV type, depending on which SV we are looking at.
						#this is because if we have a deletion, there could still be effects from duplications in the same TAD, because we exclude genes overlapped by duplications to see dup effects.
						#but for deletions, this is not relevant, and we should remove all such mutations.

						if svType == 'DEL':
							#only for a deletion, we do not need to print the deleted genes.
							#if a gene is deleted, the deletion will never result in the gain effect.
							#this is only true for deletions.

							if gene[3].name in svPatientsDel[sample] or gene[3].name in cnvPatientsDel[sample]:
								continue
						
					
						
						
						
						if str(float(geneZScores[patient,2])) == 'nan':
							continue
						
						finalScore = 0
						if randomExpression == 'True':
							import random
							randInd = random.sample(range(0, zScores.shape[0]), 1)[0]
							finalScore = float(zScores[randInd,2])
						else:
							finalScore = float(geneZScores[patient,2])

						if expressionCutoff == 'True':
							if finalScore < 1.5 and finalScore > -1.5:
								continue
							
						allGeneZScores.append(finalScore)
						
						print('RT: ', binInd, geneName, geneZScores[patient,0], finalScore)
						# import random
						# randInd = random.sample(range(0, zScores.shape[0]), 1)[0]
						# randomScore = float(zScores[randInd,2])
						# finalScore = float(geneZScores[patient,2])
						# 
						# allGeneZScores.append(abs(finalScore - randomScore) * np.sign(finalScore))
						# print('RT: ', binInd, geneName, geneZScores[patient,0], abs(finalScore - randomScore))
						# 
			if len(allGeneZScores) > 0:
				#binZScores[binInd+bins].append(np.mean(allGeneZScores))
				binZScores[binInd+bins] += allGeneZScores
				
	#divide the region into 3 bins on each side.
	#so, get the coordinates on each side depending on where the TAD pair starts and ends
	#determine which genes are in these regions
	#add the additional bins.
	
	binZScoresOffset = dict()
	for binInd in range(0, 40):
			
		if binInd not in binZScoresOffset:
			binZScoresOffset[binInd] = []
	
	for binInd in range(0, bins*2):
		binZScoresOffset[binInd+10] = binZScores[binInd]
	
	binZScoresPerPatientOffset = dict()
	for patient in allPatients:
		binZScoresPerPatientOffset[patient] = dict()
		
		for binInd in range(0, 40):
			binZScoresPerPatientOffset[patient][binInd] = []
			
		for binInd in range(0, bins*2):
			binZScoresPerPatientOffset[patient][binInd+10] = binZScoresPerPatient[patient][binInd]
	
	#get the expression data
	expressionFile = settings.files['expressionFile']

	expressionData = []
	samples = []
	with open(expressionFile, 'r') as inF:
		lineCount = 0
		for line in inF:
			line = line.strip()
			if lineCount == 0:
				samples = ['']
				samples += line.split("\t")

				lineCount += 1
				continue
			splitLine = line.split("\t")
			fullGeneName = splitLine[0]
			if fullGeneName not in geneNameConversionMap:
				continue
			geneName = geneNameConversionMap[fullGeneName] #get the gene name rather than the ENSG ID

			data = splitLine[1:len(splitLine)]
			fixedData = [geneName]
			fixedData += data
			expressionData.append(fixedData)

	expressionData = np.array(expressionData, dtype="object")

	#generate the randomized expression for the regions outside the TAD boundaries
	if randomExpression == 'True':
		from copy import deepcopy
		randomizedExpressionMatrices = []
		shuffleIterations = 1
		for i in range(0,shuffleIterations):
			genes = expressionData[:,0]
			expression = deepcopy(expressionData[:,1:])
			expressionT = expression.T
			np.random.shuffle(expressionT)
			shuffledExpression = expressionT.T
			shuffledExpressionData = np.empty(expressionData.shape, dtype='object')
			shuffledExpressionData[:,0] = genes
			shuffledExpressionData[:,1:] = shuffledExpression

			randomizedExpressionMatrices.append(shuffledExpressionData)

		expressionData = randomizedExpressionMatrices[0]

	#pre-filter expression data, for the positive and negative set in the adjacent TADs.
	filteredExpressionData = dict()
	for sampleInd in range(0, len(samples)):
		sample = samples[sampleInd]

		if sample == '':
			continue

		if sample not in filteredExpressionData:
			filteredExpressionData[sample] = dict()

		for row in expressionData:
			geneName = row[0]

			#if geneName in svPatients[sample] or geneName in snvPatients[sample] or geneName in cnvPatients[sample]:
			#	continue
			filteredExpressionData[sample][geneName] = float(row[sampleInd])

	#np.save('filteredExpressionData.npy', filteredExpressionData)
	#filteredExpressionData = np.load('filteredExpressionData.npy', allow_pickle=True, encoding='latin1').item()

	affectedCount = 0
	tadPositiveAndNegativeSet = []
	with open('output/HMF_BRCA/tadDisruptionsZScores/tadPositiveAndNegativeSet.txt', 'r') as inF:
	#with open('tadPositiveAndNegativeSet.txt', 'r') as inF:
		for line in inF:

			splitLine = line.split('\t')
			tad = splitLine[0]
			positiveSet = ast.literal_eval(splitLine[1])
			negativeSet = ast.literal_eval(splitLine[2])
			svTypes = ast.literal_eval(splitLine[3])

			if len(positiveSet) > 0:
				affectedCount += 1

			tadPositiveAndNegativeSet.append([tad, positiveSet, negativeSet, svTypes])

	tadPositiveAndNegativeSet = np.array(tadPositiveAndNegativeSet, dtype='object')
	print('affected tads: ', affectedCount)


	#so instead of looking at a region around the TADs, use the TADs that are not affected.
	#so per pair, find where it is in the positive/negative set file
	#get the previous or next one
	#check if this tad is affected or not
	#if the tad is not affected, add the same amount of bins as the affected tads and plot these on the left and right.

	for tad in tadPairs:

		splitTad = tad.split('_')
		leftTad = splitTad[0] + '_' + splitTad[1] + '_' + splitTad[2]

		#get the TAD to the left of this tad pair
		leftTadPosition = np.where(tadPositiveAndNegativeSet[:,0] == leftTad)[0]

		leftAdjacentTad = tadPositiveAndNegativeSet[leftTadPosition-1][0]
		splitLeftAdjacentTad = leftAdjacentTad[0].split('_')
		leftNegativeSet = leftAdjacentTad[2]

		splitPos = splitLeftAdjacentTad[0].split('_')

		if splitPos[0] != splitTad[0]: #check if the TAD is on the next chromosome
			continue

		#check if this TAD is disrupted, if yes, skip this TAD pair
		#if len(leftAdjacentTad[1]) > 0:
		#	continue

		#otherwise, divide this tad into bins, and get the z-scores of z-scores for the genes.
		binSizeTad1 = (float(splitLeftAdjacentTad[2]) - float(splitLeftAdjacentTad[1])) / bins
		currentStart = float(splitLeftAdjacentTad[1]) #start at the TAD start

		binStartsTad1 = [currentStart] #list at which position each bin should start.
		for binInd in range(0, bins):

			currentStart += binSizeTad1
			binStartsTad1.append(currentStart)

		#Go through the genes of the first TAD; find the genes that will be in this bin
		geneChrSubset = allGenes[allGenes[:,0] == splitLeftAdjacentTad[0]]

		for binInd in range(0, len(binStartsTad1)-1):

			#get the genes in this bin
			genes = geneChrSubset[(geneChrSubset[:,2] >= binStartsTad1[binInd]) * (geneChrSubset[:,1] <= binStartsTad1[binInd+1])]

			#get the z-scores of these genes
			allGeneZScores = []
			geneZScoresPerPatient = dict()
			for gene in genes:
				geneName = gene[3].name

				#get the expression of this gene in the negative set
				negativeExpr = []
				positiveExpr = []

				if geneName not in expressionData[:,0]:

					continue

				positiveSampleInd = []
				negativeSampleInd = []
				positivePatients = []
				negativePatients = []
				for sample in range(0, len(samples)):

					if samples[sample] == '':
						continue

					#we use the tad itself to define the positive set.
					#based on the left adjacent tad, we define the negative set.
					if samples[sample] in perTadPositivePatients[tad]:

						if samples[sample] in leftAdjacentTad[1]: #skip if this patient has a disruption of the adjacent TAD.
							continue

						#exclude this gene if it overlaps a mutation
						if geneName in svPatients[samples[sample]] or geneName in snvPatients[samples[sample]] or geneName in cnvPatients[samples[sample]]:

							continue

						positiveSampleInd.append(sample)
						positiveExpr.append(filteredExpressionData[samples[sample]][geneName])
						positivePatients.append(samples[sample])
					elif samples[sample] in leftNegativeSet:

						#exclude this gene if it overlaps a mutation
						if geneName in svPatients[samples[sample]] or geneName in snvPatients[samples[sample]] or geneName in cnvPatients[samples[sample]]:

							continue

						negativeExpr.append(filteredExpressionData[samples[sample]][geneName])
						negativePatients.append(samples[sample])
						negativeSampleInd.append(sample)

				for patientInd in range(0, len(positiveExpr)):
					patient = positiveExpr[patientInd]





					if float(np.std(negativeExpr)) == 0:

						continue

					z = (float(patient) - np.mean(negativeExpr)) / float(np.std(negativeExpr))

					if str(z) == 'nan':
						continue
					
					if expressionCutoff == 'True':
						if z > -1.5 and z < 1.5:
							continue

					print('LAT: ', binInd, geneName, positivePatients[patientInd], z)
					
					allGeneZScores.append(z)
					# import random
					# randInd = random.sample(range(0, zScores.shape[0]), 1)[0]
					# randomScore = float(zScores[randInd,2])
					# allGeneZScores.append(abs(z-randomScore) * np.sign(z))
					# 
					# print('LAT: ', binInd, geneName, positivePatients[patientInd], abs(z-randomScore))

			if len(allGeneZScores) > 0:
				#binZScoresOffset[binInd].append(np.mean(allGeneZScores))

				binZScoresOffset[binInd] += allGeneZScores

		#repeat for right TAD
		rightTad = splitTad[3] + '_' + splitTad[4] + '_' + splitTad[5]

		#get the TAD to the left of this tad pair
		rightTadPosition = np.where(tadPositiveAndNegativeSet[:,0] == rightTad)[0]

		if rightTadPosition+1 >= len(tadPositiveAndNegativeSet):
			continue #TAD is outside the genome.

		rightAdjacentTad = tadPositiveAndNegativeSet[rightTadPosition+1][0]
		splitRightAdjacentTad = rightAdjacentTad[0].split('_')
		rightNegativeSet = rightAdjacentTad[2]

		splitPos = splitRightAdjacentTad[0].split('_')
		if splitPos[0] != splitTad[3]: #check if the TAD is on the next chromosome
			continue

		#otherwise, divide this tad into bins, and get the z-scores of z-scores for the genes.
		binSizeTad1 = (float(splitRightAdjacentTad[2]) - float(splitRightAdjacentTad[1])) / bins
		currentStart = float(splitRightAdjacentTad[1]) #start at the TAD start

		binStartsTad1 = [currentStart] #list at which position each bin should start.
		for binInd in range(0, bins):

			currentStart += binSizeTad1
			binStartsTad1.append(currentStart)

		#Go through the genes of the first TAD; find the genes that will be in this bin
		geneChrSubset = allGenes[allGenes[:,0] == splitRightAdjacentTad[0]]

		for binInd in range(0, len(binStartsTad1)-1):


			#get the genes in this bin
			genes = geneChrSubset[(geneChrSubset[:,2] >= binStartsTad1[binInd]) * (geneChrSubset[:,1] <= binStartsTad1[binInd+1])]

			#get the z-scores of these genes
			allGeneZScores = []
			geneZScoresPerPatient = dict()
			for gene in genes:
				geneName = gene[3].name

				#get the expression of this gene in the negative set
				negativeExpr = []
				positiveExpr = []

				if geneName not in expressionData[:,0]:

					continue

				#geneExpr = expressionData[expressionData[:,0] == geneName][0]

				positiveSampleInd = []
				negativeSampleInd = []
				positivePatients = []
				negativePatients = []
				for sample in range(0, len(samples)):

					if samples[sample] == '':
						continue

					#we use the tad itself to define the positive set.
					#based on the left adjacent tad, we define the negative set.
					if samples[sample] in perTadPositivePatients[tad]:

						if samples[sample] in rightAdjacentTad[1]: #skip if this patient has a disruption of the adjacent TAD.
							continue

						#exclude this gene if it overlaps a mutation
						if geneName in svPatients[samples[sample]] or geneName in snvPatients[samples[sample]] or geneName in cnvPatients[samples[sample]]:
							continue

						positiveSampleInd.append(sample)
						positiveExpr.append(filteredExpressionData[samples[sample]][geneName])
						positivePatients.append(samples[sample])
					elif samples[sample] in rightNegativeSet:

						#exclude this gene if it overlaps a mutation
						if geneName in svPatients[samples[sample]] or geneName in snvPatients[samples[sample]] or geneName in cnvPatients[samples[sample]]:
							continue

						negativeExpr.append(filteredExpressionData[samples[sample]][geneName])
						negativePatients.append(samples[sample])
						negativeSampleInd.append(sample)


				for patientInd in range(0, len(positiveExpr)):
					patient = positiveExpr[patientInd]

					


					if float(np.std(negativeExpr)) == 0:
						continue

					

					z = (float(patient) - np.mean(negativeExpr)) / float(np.std(negativeExpr))

					if str(z) == 'nan':
						continue
					
					if expressionCutoff == 'True':
						if z > -1.5 and z < 1.5:
							continue
						
					print('RAT: ', binInd, geneName, positivePatients[patientInd], z)

					allGeneZScores.append(z)
					# import random
					# randInd = random.sample(range(0, zScores.shape[0]), 1)[0]
					# randomScore = float(zScores[randInd,2])
					# allGeneZScores.append(abs(z-randomScore) * np.sign(z))
					#
					# print('RAT: ', binInd, geneName, positivePatients[patientInd], abs(z-randomScore))


			if len(allGeneZScores) > 0:

				#binZScoresOffset[binInd+30].append(np.mean(allGeneZScores))
				binZScoresOffset[binInd+30] += allGeneZScores


	return binZScoresOffset

## based on DEGs

svTypes = ['DEL', 'DUP', 'INV', 'ITX']

outDir = sys.argv[1]
rules = sys.argv[3] #apply rules yes/no
cosmicRules = sys.argv[4] #look at cosmic genes with rules yes/no
expressionCutoff = sys.argv[5] #use > 1.5 and < -1.5 cutoff to show genes with differences
randomExpression = sys.argv[6]

outFilePrefix = ''

rulesName = 'rules'
cosmicRulesName = 'cosmicRules'
expressionCutoffName = 'zScoreCutoff'
randomExpressionName = 'random'

if rules == 'True':
	outFilePrefix += rulesName
	outFilePrefix += '_'
if cosmicRules == 'True':
	outFilePrefix += cosmicRulesName
	outFilePrefix += '_'
if expressionCutoff == 'True':
	outFilePrefix += expressionCutoffName
	outFilePrefix += '_'
if randomExpression == 'True':
	outFilePrefix += randomExpressionName
	outFilePrefix += '_'
# #get the z-scores per bin
# for svType in svTypes:
#
# 	#get the right zScore file here depending on if we shuffle or not
# 	if randomExpression == 'False':
# 		zScores = np.loadtxt('output/HMF_BRCA/tadDisruptionsZScores/zScores.txt', dtype='object')
# 	else:
# 		zScores = np.loadtxt('output/HMF_BRCA/tadDisruptionsZScores/zScores_random.txt', dtype='object')
# 	binScores = getBinScores(zScores, rules, cosmicRules, expressionCutoff, randomExpression, svType)
#
#
# 	print('plotting')
#
# 	allData = []
#
# 	for binInd in range(0, len(binScores)):
# 		allData.append(binScores[binInd])
#
#
# 	np.save(outFilePrefix + svType + '.npy', allData)
# exit()


###combined figures



colors = ['blue', 'red', 'magenta', 'black']
offsets = [-0.25, -0.1, 0.1, 0.25]
#colors = plt.cm.RdYlBu(np.linspace(0,1,4))
typeInd = -1
for svType in svTypes:
	print(svType)
	typeInd += 1
	
	allData = np.load(outFilePrefix + svType + '.npy', allow_pickle=True, encoding='latin1')
	#allData = allData[0]
	#if svType not in ['DEL', 'DUP']:
	#	allData = allData[0]

	#first combine bins
	
	combinedBins = [0]*20
	for binInd in range(0, len(allData)):

		if binInd < 20:
			combinedBins[binInd] = allData[binInd]
		elif binInd > 19 and binInd < 30:
			combinedBins[binInd-10] += allData[binInd]
		else:
			combinedBins[binInd-30] += allData[binInd]

	medianData = []
	upperQuantiles = []
	lowerQuantiles = []
	for binInd in range(0, len(combinedBins)):
		
		if len(combinedBins[binInd]) > 0:
			#print(combinedBins[binInd])
			median = np.mean(combinedBins[binInd])
			upperQuantile = np.quantile(combinedBins[binInd], 0.95) #0.75/25
			lowerQuantile = np.quantile(combinedBins[binInd], 0.05)
		else:
			median = 0
			upperQuantile = 0
			lowerQuantile = 0
		
		medianData.append(median)
		
		upperQuantiles.append(upperQuantile-median)
		lowerQuantiles.append(median-lowerQuantile)
		
	print(medianData)

	plt.plot(np.arange(0, len(medianData)), medianData, color=colors[typeInd], alpha=0.5)
	#plt.plot(np.arange(0, len(upperQuantile)), upperQuantile, color=colors[typeInd], alpha=0.5)
	
	medianData = np.array(medianData)
	lowerQuantiles = np.array(lowerQuantiles)
	upperQuantiles = np.array(upperQuantiles)
	
	#plt.fill_between(np.arange(0, len(medianData)), medianData-lowerQuantile, medianData+upperQuantile, facecolor=colors[typeInd], edgecolor='black', linestyle='dashdot', antialiased=True, alpha=0.2)
	#maybe add interpolation, same for quantiles as for median
	
	
	plt.errorbar(np.arange(0, len(medianData)), medianData, yerr=[lowerQuantiles, upperQuantiles], color=colors[typeInd], capsize=5, alpha=0.3)
plt.ylim([-2,16])
plt.xticks([])
plt.savefig(outFilePrefix + '.svg')
plt.show()
exit()

# 
# ### the old 1-by-1 figures with boxplots
# svType = 'ITX'
# allData = np.load('plotData_' + svType + '_allGenes_rules_random.npy', allow_pickle=True, encoding='latin1')
# 
# plt.boxplot(allData)
# plt.ylim()
# plt.show()
# 
# filteredData = []
# for binData in allData:
# 	
# 	if len(binData) == 0:
# 		filteredData.append([])
# 		continue
# 	
# 	binData = np.array(binData)
# 	#filteredBinData = binData[binData < np.percentile(binData, 99)]
# 	filteredBinData = binData[binData < 10]
# 	filteredBinData = filteredBinData[filteredBinData > -10]
# 	filteredData.append(filteredBinData)
# 
# plt.boxplot(filteredData)
# #plt.ylim(-2,5)
# plt.ylim(-5,11)
# plt.savefig(svType + '_allGenes.svg')
# plt.show()
# #plt.savefig('distanceBased_ruleBased_' + sys.argv[1] + '_shuffled.svg')
# #plt.savefig('zScoresOfZScores_distanceBased_2.svg')
# exit()



