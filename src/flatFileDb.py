﻿#!/usr/bin/env python######### Documentation #########__author__ = "Marleen Nieboer"__credits__ = []__maintainer__ = "Marleen Nieboer"__email__ = "m.m.nieboer@umcutrecht.nl"__status__ = "Development"### Imports ###import syssys.path.append('settings/') #Add settings pathimport settingsimport numpy as np#Import the classes that interact with the files directlyfrom geneFeatureHandler import GeneFeatureHandlerfrom tadFeatureHandler import TADFeatureHandlerfrom hiCFeatureHandler import HiCFeatureHandler### Code ###class FlatFileDB:		"""		Handler for obtaining data from flat files and computing features based on these data. All direct interactions with flat files, such as reading the data from these, should preferably be done within this class. 	"""		#This function currently only reads the start, end and chromosome for easy testing. We can later return everything on the entire line and then select which ones we want based on the settings	def readGeneListFile(self):		"""			Reads the gene-related information from a flat-file with a gene list.						Returns:				geneListData (numpy matrix): a Numpy matrix with on the columns: chr, start, end, pLI, RVIS, HPO ids, HGNC symbol, and the genes on the rows. 		"""				geneListFile = settings.inputFiles['geneList']				#Read the gene list data into a list		geneListData = []		with open(geneListFile, "r") as f:			lineCount = 0			for line in f:				if lineCount < 2: #skip header					lineCount += 1					continue				line = line.strip()				splitLine = line.split("\t")								#We are interested in the positional information to see which gene is closest. (Add more later)								#Convert the numbers to integers for quicker comparison. 5 is start, 6 is end				splitLine[5] = int(splitLine[5])				splitLine[6] = int(splitLine[6])								splitLine[4] = str(splitLine[4])								#chr, start, end, pLI, RVIS, HPO ids, HGNC symbol				geneListData.append([splitLine[4], splitLine[5], splitLine[6], splitLine[10], splitLine[11], splitLine[14], splitLine[0]])				#Also convert the other dataset to numpy		geneListData = np.array(geneListData, dtype='object')			return geneListData		#I keep the annotations separate from the SVs for now, so that the original data can be re-used without having been updated multiple times already. 	def computeNearestGeneFeatures(self, regions):		"""			Function for computing features related to nearby genes. Functions as an abstraction layer between the actual feature computation and reading gene-related data. 						Parameters:				regions (numpy matrix): a Numpy matrix of dtype 'object' with on the columns chr 1, s1, e1, chr2, s2, e2, and the regions on the rows.							Returns:				annotations (dict): a dictionary with all feature names as keys, and a list of values where each value is the feature of a region. The value must be a list, even if it has only 1 value. 				"""				#First read the gene-related data		geneData = self.readGeneListFile()				#Initiate the gene list handler		geneFeatureHandler = GeneFeatureHandler()		annotations = geneFeatureHandler.annotate(regions, geneData)				#I'm not sure yet if these settings should actually make sure that specific features are not obtained (not very useful for now since everything is on one row anyway),		#or if this should be part of the object that communicates with the file, such that it also does not try to obtain those features if disabled (could save computational time)		#if settings.features['NearestGene'] is True:		#	a = 1				return annotations	def readTADFile(self):		"""			Reads the file with TADs defined in the settings into a numpy matrix. Positions are converted into integers. 						Returns:				tadData (numpy matrix): matrix with columns chr, start, end, with each TAD on the rows. 				"""		tadFile = settings.inputFiles['tads']				#Read the gene list data into a list		tadData = []		with open(tadFile, "r") as f:			lineCount = 0			for line in f:				if lineCount < 2: #skip header					lineCount += 1					continue				line = line.strip()				splitLine = line.split("\t")												#We are interested in the positional information to see which gene is closest. (Add more later)								#Convert the numbers to integers for quicker comparison. 0 is chromosome, 1 is start, 2 is end. Celltypes are not used for now. 				splitLine[1] = int(splitLine[1])				splitLine[2] = int(splitLine[2])								#chr, start, end				tadData.append([splitLine[0], splitLine[1], splitLine[2]])				#Also convert the other dataset to numpy		tadData = np.array(tadData, dtype='object')			return tadData			def computeTADFeatures(self, regions):		"""			Function for computing features related to TADs. Functions as an abstraction layer between the actual feature computation and reading TAD-related data. 						Parameters:				regions (numpy matrix): a Numpy matrix of dtype 'object' with on the columns chr 1, s1, e1, chr2, s2, e2, and the regions on the rows.							Returns:				annotations (dict): a dictionary with all feature names as keys, and a list of values where each value is the feature of a region. The value must be a list, even if it has only 1 value. 					TODO:				merge with Hi-C annotations? 				"""				#First read the TAD data from the flat file		tadData = self.readTADFile()				#Compute the TAD-related features		tadFeatureHandler = TADFeatureHandler()		annotations = tadFeatureHandler.annotate(regions, tadData)				return annotations		def readHiCDegreeFile(self):		"""			Read the data from the degree file. In the graph, the chromosome name and position are concatenated, so we separate these here. The degree data is sorted by chromosome and position. THe sorting is			lexographical, so chromosome 11 comes before chromosome 2, for example. This is ok for the purpose of annotation, since all I am interested in is subsetting by chromosome and then it does not matter			how these chromosomes are sorted. The position sorting is very important, this should alway be from low to high.						Returns:				sortedDegrees (numpy matrix): numpy matrix with sorted degree data (see above). Col 1 = chromosome name as defined in file (e.g. chr1), col 2 = position, col 3 = degree.   		"""						#1. Get the file from the settings		degreeFile = settings.inputFiles['hiCDegree']				#2. Read the file content into memory		degreeData = []		with open(degreeFile, "r") as f:			lineCount = 0			for line in f:				if lineCount < 1: #skip header					lineCount += 1					continue				line = line.strip()				splitLine = line.split(",")				#store the chromosome name and position in a different column in the final array							position = splitLine[0].replace('"', '')								splitPosition = position.split("_")								chrName = splitPosition[0]				start = splitPosition[1]				end = int(start) + 5000 #This should be a setting!								degree = splitLine[1]								degreeData.append([chrName, int(start), end, int(degree)])						#3. Sort the file (Should we already do that here?)		degreeData = np.array(degreeData, dtype='object')				chrCol = degreeData[:,0]		posCol = degreeData[:,1]				sortedInd = np.lexsort((posCol, chrCol)) #sort first by column 1, then by column 2. This works, but it is lexographical, so chromosome 11 comes before chromosome 2. For this purpose it is ok, since we only look for this													#chromosome in other files to subset these, so the order in which we do that does not really matter. 				sortedDegrees = degreeData[sortedInd]				#4. Return the data		return sortedDegrees			def computeHiCFeatures(self, regions):		"""			Function for computing features related to Hi-C interactions. Functions as an abstraction layer between the actual feature computation and reading Hi-C related measures, e.g., topology.			Currently only the degree is implemented. 						Parameters:				regions (numpy matrix): a Numpy matrix of dtype 'object' with on the columns chr 1, s1, e1, chr2, s2, e2, and the regions on the rows.							Returns:				annotations (dict): a dictionary with all feature names as keys, and a list of values where each value is the feature of a region. The value must be a list, even if it has only 1 value. 					TODO:				- Have one uniform function that collects all data and calls independent functions for reading the degree file, betweenness, etc. 				"""				#1. Read the HiC related files				#Degree file 		degreeData = self.readHiCDegreeFile()				#2. Initialize the feature handler		hiCFeatureHandler = HiCFeatureHandler()		hiCFeatureHandler.annotate(regions, degreeData)				#3. Annotate the regions with Hi-C features				#return annotations									def computeEnhancerFeatures(self, regions):				1+1			def computePCHiCFeatures(self, regions):				1+1				