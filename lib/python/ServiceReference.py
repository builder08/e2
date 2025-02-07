# -*- coding: utf-8 -*-
from enigma import eServiceReference, eServiceReferenceDVB, eServiceCenter, getBestPlayableServiceReference
from Components.config import config
import NavigationInstance

# Global helper functions


def getPlayingRef():
	playingref = None
	if NavigationInstance.instance:
		playingref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
	return playingref or eServiceReference()


def isPlayableForCur(serviceref):
	info = eServiceCenter.getInstance().info(serviceref)
	return info and info.isPlayable(serviceref, getPlayingRef())


def resolveAlternate(serviceref):
	nref = None
	if serviceref.flags & eServiceReference.isGroup:
		nref = getBestPlayableServiceReference(serviceref, getPlayingRef())
		if not nref:
			nref = getBestPlayableServiceReference(serviceref, eServiceReference(), True)
	return nref


def getStreamRelayRef(sref):
	try:
		if "http" in sref:
			icamport = config.misc.softcam_streamrelay_port.value
			icamip = ".".join("%d" % d for d in config.misc.softcam_streamrelay_url.value)
			icam = f"http%3a//{icamip}%3a{icamport}/"
			if icam in sref:
				return sref.split(icam)[1].split(":")[0].replace("%3a", ":"), True
	except Exception:
		pass
	return sref, False

# Extensions to eServiceReference

@staticmethod
def __fromDirectory(path):
	ref = eServiceReference(eServiceReference.idFile,
			eServiceReference.flagDirectory |
			eServiceReference.shouldSort | eServiceReference.sort1, path)
	ref.setData(0, 1)
	return ref
# type 1 = digital television service
# type 4 = nvod reference service (NYI)
# type 17 = MPEG-2 HD digital television service
# type 22 = advanced codec SD digital television
# type 24 = advanced codec SD NVOD reference service (NYI)
# type 25 = advanced codec HD digital television
# type 27 = advanced codec HD NVOD reference service (NYI)
# type 2 = digital radio sound service
# type 10 = advanced codec digital radio sound service
# type 31 = High Efficiency Video Coding digital television

# Generate an eServiceRef query path containing
# '(type == serviceTypes[0]) || (type == serviceTypes[1]) || ...'

def makeServiceQueryStr(serviceTypes):
	return ' || '.join(map(lambda x: '(type == %d)' % x, serviceTypes))

def serviceRefAppendPath(sref, path):
	nsref = eServiceReference(sref)
	nsref.setPath(nsref.getPath() + path)
	return nsref

eServiceReference.fromDirectory = __fromDirectory

eServiceReference.isPlayback = lambda serviceref: "0:0:0:0:0:0:0:0:0" in serviceref.toCompareString()

# Apply ServiceReference method proxies to the eServiceReference object so the two classes can be used interchangeably
# These are required for ServiceReference backwards compatibility
eServiceReference.isRecordable = lambda serviceref: serviceref.flags & eServiceReference.isGroup or (serviceref.type == eServiceReference.idDVB or serviceref.type == eServiceReference.idDVB + 0x100 or serviceref.type == 0x2000 or serviceref.type == 0x1001 or serviceref.type == eServiceReference.idServiceMP3)
service_types_tv_ref = eServiceReference(eServiceReference.idDVB, eServiceReference.flagDirectory, eServiceReferenceDVB.dTv)

service_types_tv_ref.setPath(makeServiceQueryStr((
	eServiceReferenceDVB.dTv,
	eServiceReferenceDVB.mpeg2HdTv,
	eServiceReferenceDVB.avcSdTv,
	eServiceReferenceDVB.avcHdTv,
	eServiceReferenceDVB.nvecTv,
	eServiceReferenceDVB.user134,
	eServiceReferenceDVB.user195,
)))

service_types_radio_ref = eServiceReference(eServiceReference.idDVB, eServiceReference.flagDirectory, eServiceReferenceDVB.dRadio)
service_types_radio_ref.setPath(makeServiceQueryStr((
	eServiceReferenceDVB.dRadio,
	eServiceReferenceDVB.dRadioAvc,
)))

def hdmiInServiceRef():
	return eServiceReference(eServiceReference.idServiceHDMIIn, eServiceReference.noFlags, eServiceReferenceDVB.dTv)

def __repr(serviceref):
	chnum = serviceref.getChannelNum()
	chnum = ", ChannelNum=" + str(chnum) if chnum else ""
	return "eServiceReference(Name=%s%s, String=%s)" % (serviceref.getServiceName(), chnum, serviceref.toString())
eServiceReference.__repr__ = __repr
def __toString(serviceref):
	return serviceref.toString()
eServiceReference.__str__ = __toString
def __getServiceName(serviceref):
	info = eServiceCenter.getInstance().info(serviceref)
	return info and info.getName(serviceref) or ""
eServiceReference.getServiceName = __getServiceName
def __info(serviceref):
	return eServiceCenter.getInstance().info(serviceref)
eServiceReference.info = __info
def __list(serviceref):
	return eServiceCenter.getInstance().list(serviceref)
eServiceReference.list = __list
# ref is obsolete but kept for compatibility.
# A ServiceReference *is* an eServiceReference now, so you no longer need to use .ref
def __getRef(serviceref):
	return serviceref
def __setRef(self, serviceref):
	eServiceReference.__init__(self, serviceref)
eServiceReference.ref = property(__getRef, __setRef,)
# getType is obsolete but kept for compatibility. Use "serviceref.type" instead
def __getType(serviceref):
	return serviceref.type
eServiceReference.getType = __getType
# getFlags is obsolete but kept for compatibility. Use "serviceref.flags" instead
def __getFlags(serviceref):
	return serviceref.flags
eServiceReference.getFlags = __getFlags
# Compatibility class that exposes eServiceReference as ServiceReference
# Don't use this for new code. eServiceReference now supports everything in one single type
class ServiceReference(eServiceReference):
	def __new__(cls, ref, reftype=eServiceReference.idInvalid, flags=0, path=''):
		# if trying to copy an eServiceReference object, turn it into a ServiceReference type and return it
		if reftype == eServiceReference.idInvalid and isinstance(ref, eServiceReference):
			new = ref
			new.__class__ = ServiceReference
			return new
		return eServiceReference.__new__(cls)
	def __init__(self, ref, reftype=eServiceReference.idInvalid, flags=0, path=''):
		if reftype != eServiceReference.idInvalid:
			eServiceReference.__init__(self, reftype, flags, path)
		elif not isinstance(ref, eServiceReference):
			eServiceReference.__init__(self, ref or "")
