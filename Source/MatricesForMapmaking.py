# SUPPORTING MODULE FOR JOINT MAPMAKING AND POWER SPECTRUM PIPELINE
# by Josh Dillon

import numpy as np
import healpy as hp
import math
import Geometry
import cPickle as pickle
import os

def computeNoisePerUniqueBaseline(s):
    s.noisePerUniqueBaseline = np.zeros((len(s.noisePerAntenna),len(s.baselines)))
    for antennaPair in s.antennaPairDict.keys():
        s.noisePerUniqueBaseline[:,s.antennaPairDict[antennaPair]] += 1.0 / (s.noisePerAntenna[:,antennaPair[0]] * s.noisePerAntenna[:,antennaPair[1]])**2
    s.noisePerUniqueBaseline = 1.0 / s.noisePerUniqueBaseline ** .5

def inverseCovarianceWeightVisibilities(s,visibilities):
    """This function weights the visibilities (which have not been combined into snapshots yet) by the inverse of the noise variance."""
    if s.useOnlyUniqueBaselines:
        computeNoisePerUniqueBaseline(s)
        visibilities /= (s.noisePerUniqueBaseline**2)
    else:
        print "WARNING: this has not been tested."        
        for b in range(len(s.baselines)):
            visibilities[:,b] /= (s.noisePerAntenna[:,s.allBaselinePairs[b,0]] * s.noisePerAntenna[:,s.allBaselinePairs[b,1]])

def calculateNinvTimesy(visibilities, snapshot):
    """This function computes the inverse varianced weighted sum of rephased visibilities in a snapshot. The averaging (rather than summing) happens when the normalizaiton is applied."""
    return np.sum(visibilities[snapshot.LSTindices,:], axis=0)
    
def calculateNInv(s, snapshot):
    """This function computes the diagonal of the inverse noise covariance (off-diagonal terms are 0) for each baseline during this snapshot."""
    if s.useOnlyUniqueBaselines:
        return np.sum(s.noisePerUniqueBaseline[snapshot.LSTindices,:]**(-2), axis=0)
    else:
        print "WARNING: this has not been tested."
        return np.asarray([np.sum((s.noisePerAntenna[:,s.allBaselinePairs[b,0]] * s.noisePerAntenna[:,s.allBaselinePairs[b,1]])**(-1), axis=0) for b in range(len(s.baselines))])

def calculateKAtranspose(s,snapshot,coords,PBs):
    """This function computes K_PSF * A^t, which maps baselines at the given snapshot central index to the PSF pixels.
    It is worth nothing that the Fourier convention is based on A having e^ib.k, so A^t has e^-ib.k = e^i|k|b.theta_hat, as we see here."""
    if s.useAdaptiveHEALPixForPSF:    
        realSpaceDiagonalPart = np.ones(coords.nPSFPixels) * 4*np.pi / 12.0 / coords.newPSFNSIDEs**2 / s.convertJyToKFactor
    else:
        realSpaceDiagonalPart = np.ones(coords.nPSFPixels) * 4*np.pi / 12.0 / s.mapNSIDE**2 / s.convertJyToKFactor
    PSFAlts, PSFAzs = Geometry.convertEquatorialToHorizontal(s, coords.PSFRAs, coords.PSFDecs, snapshot.centralLST)
    PSFCartVecs = Geometry.convertAltAzToCartesian(PSFAlts, PSFAzs)
    realSpaceDiagonalPart *= hp.get_interp_val(PBs.beamSquared("X","x",s.pointings[snapshot.centralLSTIndex]), np.pi/2-PSFAlts, PSFAzs)
    KAtranspose = np.dot(np.diag(realSpaceDiagonalPart), np.exp(1j * s.k * np.dot(PSFCartVecs,np.transpose(s.baselines))))
    return KAtranspose
    
def calculatePSAmatrix(s,snapshot,ps,PBs):
    """This function computes A mappings to the locations of the point source at the snapshot central index to the baselines."""
    psAlts, psAzs = Geometry.convertEquatorialToHorizontal(s, ps.RAs, ps.decs, snapshot.centralLST)
    psCartVecs = Geometry.convertAltAzToCartesian(psAlts, psAzs)
    realSpaceDiagonalPart = hp.get_interp_val(PBs.beamSquared("X","x",s.pointings[snapshot.centralLSTIndex]), np.pi/2-psAlts, psAzs)
    pointSourceAmatrix = np.dot(np.exp(-1j * s.k * s.baselines.dot(np.transpose(psCartVecs))), np.diag(realSpaceDiagonalPart))
    return pointSourceAmatrix
    
def saveAllResults(s,times,ps,Dmatrix,PSF,coaddedMap,pointSourcePSF):
    """This function saves all the input classes, vectors, and matrices to s.resultsFolder."""
    print "Now writing results to " + s.resultsFolder
    pickle.dump(s, open(s.resultsFolder + "specifications.p","wb"))
    pickle.dump(times, open(s.resultsFolder + "times.p","wb"))
    pickle.dump(ps, open(s.resultsFolder + "pointSourceCatalog.p","wb"))
    np.save(s.resultsFolder + "Dmatrix",np.diag(Dmatrix))
    np.save(s.resultsFolder + "PSF",PSF)
    np.save(s.resultsFolder + "coaddedMap",coaddedMap)
    if s.PSFforPointSources and ps.nSources > 0:
        np.save(s.resultsFolder + "pointSourcePSF",pointSourcePSF)

def loadAllResults(resultsFolder):
    s = pickle.load(open(resultsFolder + "specifications.p","rb"))
    times = pickle.load( open(resultsFolder + "times.p","rb"))
    ps = pickle.load(open(resultsFolder + "pointSourceCatalog.p","rb"))
    Dmatrix = np.load(resultsFolder + "Dmatrix.npy")
    PSF = np.load(resultsFolder + "PSF.npy")
    coaddedMap = np.load(resultsFolder + "coaddedMap.npy")
    if s.PSFforPointSources and ps.nSources>0:
        pointSourcePSF = np.load(resultsFolder + "pointSourcePSF.npy")
        return s, times, ps, Dmatrix, PSF, coaddedMap, pointSourcePSF
    else:
        return s, times, ps, Dmatrix, PSF, coaddedMap, []

