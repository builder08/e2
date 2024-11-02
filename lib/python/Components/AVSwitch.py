from os.path import exists
from os import W_OK, access, system
from time import sleep

from enigma import eAVSwitch, eAVControl, getDesktop

from Components.config import config, ConfigSlider, ConfigSelection, ConfigYesNo, ConfigEnableDisable, ConfigSubsection, ConfigBoolean, ConfigSelectionNumber, ConfigNothing, ConfigOnOff, NoSave
from Components.SystemInfo import BoxInfo
from Tools.AVHelper import pChoice, readChoices
from Tools.Directories import fileReadLine, fileWriteLine

iAVSwitch = None # will be initialized later, allows to import name 'iAVSwitch' from 'Components.AVSwitch'

MODULE_NAME = __name__.split(".")[-1]

MODEL = BoxInfo.getItem("model")
AMLOGIC = BoxInfo.getItem("AmlogicFamily")

class AVSwitch:
	def setAspect(self, configElement):
		eAVControl.getInstance().setAspect(configElement.value, 1)

	def setAspectRatio(self, value):
		if value < 100:
			eAVControl.getInstance().setAspectRatio(value)
		else:  # Aspect Switcher
			value -= 100
			offset = config.av.aspectswitch.offsets[str(value)].value
			newheight = 576 - offset
			newtop = offset // 2
			if value:
				newwidth = 720
			else:
				newtop = 0
				newwidth = 0
				newheight = 0

			eAVControl.getInstance().setAspectRatio(2)  # 16:9
			eAVControl.getInstance().setVideoSize(newtop, 0, newwidth, newheight)

	def setColorFormat(self, value):
		eAVSwitch.getInstance().setColorFormat(value)

	def setInput(self, input):
		eAVControl.getInstance().setInput(input, 1)

	def setSystem(self, value):
		eAVSwitch.getInstance().setVideomode(value)

	def getOutputAspect(self):
		valstr = config.av.aspectratio.value
		if valstr in ("4_3_letterbox", "4_3_panscan"):  # 4:3
			return (4, 3)
		elif valstr == "16_9":  # auto ... 4:3 or 16:9
			if exists("/proc/stb/vmpeg/0/aspect"):
				try:
					if "1" in open("/proc/stb/vmpeg/0/aspect", "r").read().split('\n', 1)[0]: # 4:3
						return (4, 3)
				except IOError:
					print("[AVSwitch] Read /proc/stb/vmpeg/0/aspect failed!")
			elif exists("/sys/class/video/screen_mode"):
				try:
					if "1" in open("/sys/class/video/screen_mode", "r").read().split('\n', 1)[0]: # 4:3
						return (4, 3)
				except IOError:
					print("[AVSwitch] Read /sys/class/video/screen_mode failed!")
		elif valstr in ("16_9_always", "16_9_letterbox"):  # 16:9
			pass
		elif valstr in ("16_10_letterbox", "16_10_panscan"):  # 16:10
			return (16, 10)
		return (16, 9)

	def getFramebufferScale(self):
		aspect = self.getOutputAspect()
		fb_size = getDesktop(0).size()
		return (aspect[0] * fb_size.height(), aspect[1] * fb_size.width())

	def getAspectRatioSetting(self):
		valstr = config.av.aspectratio.value
		if valstr == "4_3_letterbox":
			val = 0
		elif valstr == "4_3_panscan":
			val = 1
		elif valstr == "16_9":
			val = 2
		elif valstr == "16_9_always":
			val = 3
		elif valstr == "16_10_letterbox":
			val = 4
		elif valstr == "16_10_panscan":
			val = 5
		elif valstr == "16_9_letterbox":
			val = 6
		return val

	def setAspectWSS(self, aspect=None):
		if not config.av.wss.value:
			value = 2  # auto(4:3_off)
		else:
			value = 1  # auto
		eAVSwitch.getInstance().setWSS(value)


def InitAVSwitch():
	config.av = ConfigSubsection()
	if MODEL == "vuduo":
		config.av.yuvenabled = ConfigBoolean(default=False)
	else:
		config.av.yuvenabled = ConfigBoolean(default=True)
	colorformat_choices = {"cvbs": "CVBS"}

	config.av.osd_alpha = ConfigSlider(default=255, increment=5, limits=(20, 255))  # Make Openpli compatible with some plugins who still use config.av.osd_alpha.

	# when YUV, Scart or S-Video is not support by HW, don't let the user select it
	if BoxInfo.getItem("HasYPbPr"):
		colorformat_choices["yuv"] = "YPbPr"
	if BoxInfo.getItem("HasScart"):
		colorformat_choices["rgb"] = "RGB"
	if BoxInfo.getItem("HasSVideo"):
		colorformat_choices["svideo"] = "S-Video"

	config.av.colorformat = ConfigSelection(choices=colorformat_choices, default="rgb")
	config.av.aspectratio = ConfigSelection(choices={
			"4_3_letterbox": _("4:3 letterbox"),
			"4_3_panscan": _("4:3 panscan"),
			"16_9": _("16:9"),
			"16_9_always": _("16:9 always"),
			"16_10_letterbox": _("16:10 letterbox"),
			"16_10_panscan": _("16:10 panscan"),
			"16_9_letterbox": _("16:9 letterbox")},
			default="16_9")
	config.av.aspect = ConfigSelection(choices={
			"4_3": _("4:3"),
			"16_9": _("16:9"),
			"16_10": _("16:10"),
			"auto": _("Automatic")},
			default="auto")

	if exists("/proc/stb/video/policy2"):
		if exists("/proc/stb/video/policy2_choices"):
			policy2_choices_proc = "/proc/stb/video/policy2_choices"
		else:
			if exists("/proc/stb/video/policy_choices"):
				policy2_choices_proc = "/proc/stb/video/policy_choices"
			else:
				policy2_choices_proc = None
		try:
			policy2_choices_raw = open(policy2_choices_proc, "r").read()
		except:
			policy2_choices_raw = "letterbox"

		policy2_choices = {}

		if policy2_choices_raw and policy2_choices_raw is not None:
			if "letterbox" in policy2_choices_raw:
				policy2_choices.update({"letterbox": _("Letterbox")})
			if "panscan" in policy2_choices_raw:
				policy2_choices.update({"panscan": _("Pan&scan")})
			if "nonliner" in policy2_choices_raw and not "nonlinear" in policy2_choices_raw:
				policy2_choices.update({"nonliner": _("Stretch nonlinear")})
			if "nonlinear" in policy2_choices_raw:
				policy2_choices.update({"nonlinear": _("Stretch nonlinear")})
			if "scale" in policy2_choices_raw and not "auto" in policy2_choices_raw and not "bestfit" in policy2_choices_raw:
				policy2_choices.update({"scale": _("Stretch linear")})
			if "full" in policy2_choices_raw:
				policy2_choices.update({"full": _("Stretch full")})
			if "auto" in policy2_choices_raw and not "bestfit" in policy2_choices_raw:
				policy2_choices.update({"auto": _("Stretch linear")})
			if "bestfit" in policy2_choices_raw:
				policy2_choices.update({"bestfit": _("Stretch linear")})
		config.av.policy_169 = ConfigSelection(choices=policy2_choices, default="letterbox")

	if exists("/proc/stb/video/policy_choices"):
		policy_choices_proc = "/proc/stb/video/policy_choices"
	else:
		policy_choices_proc = None
	try:
		policy_choices_raw = open(policy_choices_proc, "r").read()
	except:
		policy_choices_raw = "panscan"

	policy_choices = {}

	if policy_choices_raw and policy_choices_raw is not None:
		if "pillarbox" in policy_choices_raw and not "panscan" in policy_choices_raw:
			policy_choices.update({"pillarbox": _("Pillarbox")})
		if "panscan" in policy_choices_raw:
			policy_choices.update({"panscan": _("Pillarbox")})
		if "letterbox" in policy_choices_raw:
			policy_choices.update({"letterbox": _("Pan&scan")})
		if "nonliner" in policy_choices_raw and not "nonlinear" in policy_choices_raw:
			policy_choices.update({"nonliner": _("Stretch nonlinear")})
		if "nonlinear" in policy_choices_raw:
			policy_choices.update({"nonlinear": _("Stretch nonlinear")})
		if "scale" in policy_choices_raw and not "auto" in policy_choices_raw and not "bestfit" in policy_choices_raw:
			policy_choices.update({"scale": _("Stretch linear")})
		if "full" in policy_choices_raw:
			policy_choices.update({"full": _("Stretch full")})
		if "auto" in policy_choices_raw and not "bestfit" in policy_choices_raw:
			policy_choices.update({"auto": _("Stretch linear")})
		if "bestfit" in policy_choices_raw:
			policy_choices.update({"bestfit": _("Stretch linear")})
	config.av.policy_43 = ConfigSelection(choices=policy_choices, default="panscan")

	config.av.tvsystem = ConfigSelection(choices={"pal": "PAL", "ntsc": "NTSC", "multinorm": "multinorm"}, default="pal")
	config.av.wss = ConfigEnableDisable(default=True)
	config.av.generalAC3delay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
	config.av.generalPCMdelay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
	config.av.vcrswitch = ConfigEnableDisable(default=False)

	def setColorFormat(configElement):
		if MODEL == "et6x00":
			map = {"cvbs": 3, "rgb": 3, "svideo": 2, "yuv": 3}
		elif MODEL == "gb7356" or MODEL.startswith('et'):
			map = {"cvbs": 0, "rgb": 3, "svideo": 2, "yuv": 3}
		else:
			map = {"cvbs": 0, "rgb": 1, "svideo": 2, "yuv": 3}
		iAVSwitch.setColorFormat(map[configElement.value])
	config.av.colorformat.addNotifier(setColorFormat)

	def setAspectRatio(configElement):
		map = {"4_3_letterbox": 0, "4_3_panscan": 1, "16_9": 2, "16_9_always": 3, "16_10_letterbox": 4, "16_10_panscan": 5, "16_9_letterbox": 6}
		iAVSwitch.setAspectRatio(map[configElement.value])

	def setSystem(configElement):
		map = {"pal": 0, "ntsc": 1, "multinorm": 2}
		iAVSwitch.setSystem(map[configElement.value])

	def setWSS(configElement):
		iAVSwitch.setAspectWSS()

	# this will call the "setup-val" initial
	config.av.aspectratio.addNotifier(setAspectRatio)
	config.av.tvsystem.addNotifier(setSystem)
	config.av.wss.addNotifier(setWSS)

	iAVSwitch.setInput("ENCODER")  # init on startup

	BoxInfo.setItem("ScartSwitch", eAVControl.getInstance().hasScartSwitch())

	bypassEDID = fileReadLine("/proc/stb/hdmi/bypass_edid_checking", default=None, source=MODULE_NAME)
	bypassEDID = bypassEDID.split() if bypassEDID else False
	BoxInfo.setItem("Canedidchecking", bypassEDID)
	if bypassEDID:
		def setEDIDBypass(configElement):
			if configElement.value:
				value = "00000001" if configElement.value else "00000000"
				fileWriteLine("/proc/stb/hdmi/bypass_edid_checking", value, source=MODULE_NAME)

		config.av.bypass_edid_checking = ConfigYesNo(default=True)
		config.av.bypass_edid_checking.addNotifier(setEDIDBypass)
	else:
		config.av.bypass_edid_checking = ConfigNothing()
	colorspace = fileReadLine("/proc/stb/video/hdmi_colorspace", default=None, source=MODULE_NAME)
	colorspace = colorspace.split() if colorspace else False
	BoxInfo.setItem("havecolorspace", colorspace)
	if colorspace:
		def setHDMIColorspace(configElement):
			fileWriteLine("/proc/stb/video/hdmi_colorspace", configElement.value, source=MODULE_NAME)

		if MODEL in ("vusolo4k", "vuuno4k", "vuuno4kse", "vuultimo4k", "vuduo4k", "vuduo4kse"):
			default = "Edid(Auto)"
			choiceList = [
				("Edid(Auto)", _("Auto")),
				("Hdmi_Rgb", "RGB"),
				("444", "YCbCr 444"),
				("422", "YCbCr 422"),
				("420", "YCbCr 420")
			]
		elif MODEL in ("dm900", "dm920", "vuzero4k"):
			default = "Edid(Auto)"
			choiceList = [
				("Edid(Auto)", _("Auto")),
				("Hdmi_Rgb", "RGB"),
				("Itu_R_BT_709", "BT.709"),
				("DVI_Full_Range_RGB", _("Full Range RGB")),
				("FCC", "FCC 1953"),
				("Itu_R_BT_470_2_BG", "BT.470 BG"),
				("Smpte_170M", "SMPTE 170M"),
				("Smpte_240M", "SMPTE 240M"),
				("Itu_R_BT_2020_NCL", "BT.2020 NCL"),
				("Itu_R_BT_2020_CL", "BT.2020 CL"),
				("XvYCC_709", "BT.709 XvYCC"),
				("XvYCC_601", "BT.601 XvYCC")
			]
		else:
			default = "auto"
			choiceList = [
				("auto", _("Auto")),
				("rgb", "RGB"),
				("420", "YCbCr 420"),
				("422", "YCbCr 422"),
				("444", "YCbCr 444")
			]
		config.av.hdmicolorspace = ConfigSelection(default=default, choices=choiceList)
		config.av.hdmicolorspace.addNotifier(setHDMIColorspace)
	else:
		config.av.hdmicolorspace = ConfigNothing()
	colorimetry = fileReadLine("/proc/stb/video/hdmi_colorimetry", default=None, source=MODULE_NAME)
	colorimetry = colorimetry.split() if colorimetry else False
	BoxInfo.setItem("havecolorimetry", colorimetry)
	if colorimetry:
		def setHDMIColorimetry(configElement):
			sleep(0.1)
			fileWriteLine("/proc/stb/video/hdmi_colorimetry", configElement.value, source=MODULE_NAME)

		config.av.hdmicolorimetry = ConfigSelection(default="auto", choices=[
			("auto", _("Auto")),
			("bt2020ncl", "BT.2020 NCL"),
			("bt2020cl", "BT.2020 CL"),
			("bt709", "BT.709")
		])
		config.av.hdmicolorimetry.addNotifier(setHDMIColorimetry)
	else:
		config.av.hdmicolorimetry = ConfigNothing()
	boxMode = fileReadLine("/proc/stb/info/boxmode", default=None, source=MODULE_NAME)
	boxMode = boxMode.split() if boxMode else False
	BoxInfo.setItem("haveboxmode", boxMode)
	if boxMode:
		def setBoxMode(configElement):
			fileWriteLine("/proc/stb/info/boxmode", configElement.value, source=MODULE_NAME)

		config.av.boxmode = ConfigSelection(default="12", choices=[
			("12", _("Enable PiP no HDR")),
			("1", _("12bit 4:2:0/4:2:2 no PiP"))
		])
		config.av.boxmode.addNotifier(setBoxMode)
	else:
		config.av.boxmode = ConfigNothing()
	colorDepth = fileReadLine("/proc/stb/video/hdmi_colordepth", default=None, source=MODULE_NAME)
	colorDepth = colorDepth.split() if colorDepth else False
	BoxInfo.setItem("havehdmicolordepth", colorDepth)
	if colorDepth:
		def setColorDepth(configElement):
			fileWriteLine("/proc/stb/video/hdmi_colordepth", configElement.value, source=MODULE_NAME)

		config.av.hdmicolordepth = ConfigSelection(default="auto", choices=[
			("auto", _("Auto")),
			("8bit", _("8bit")),
			("10bit", _("10bit")),
			("12bit", _("12bit"))
		])
		config.av.hdmicolordepth.addNotifier(setColorDepth)
	else:
		config.av.hdmicolordepth = ConfigNothing()

	syncMode = fileReadLine("/proc/stb/video/sync_mode_choices", default=None, source=MODULE_NAME)
	syncMode = syncMode.split() if syncMode else False
	BoxInfo.setItem("havesyncmode", syncMode)
	if syncMode:
		def setSyncMode(configElement):
			fileWriteLine("/proc/stb/video/sync_mode", configElement.value, source=MODULE_NAME)

		config.av.sync_mode = ConfigSelection(default="slow", choices=[
			("slow", _("Slow Motion")),
			("hold", _("Hold First Frame")),
			("black", _("Black Screen")),
		])
		config.av.sync_mode.addNotifier(setSyncMode)
	else:
		config.av.sync_mode = ConfigNothing()
	AMLHDRSupport = exists("/sys/class/amhdmitx/amhdmitx0/config")
	BoxInfo.setItem("haveamlhdrsupport", AMLHDRSupport)
	if AMLHDRSupport:
		def setAMLHDR10(configElement):
			fileWriteLine("/sys/class/amhdmitx/amhdmitx0/config", configElement.value, source=MODULE_NAME)

		def setAMLHLG(configElement):
			fileWriteLine("/sys/class/amhdmitx/amhdmitx0/config", configElement.value, source=MODULE_NAME)

		config.av.amlhdr10_support = ConfigSelection(default="hdr10-2", choices=[
			("hdr10-0", _("Force enabled")),
			("hdr10-1", _("Force disabled")),
			("hdr10-2", _("Controlled by HDMI"))
		])
		config.av.amlhdr10_support.addNotifier(setAMLHDR10)
		config.av.amlhlg_support = ConfigSelection(default="hlg-2", choices=[
			("hlg-0", _("Force enabled")),
			("hlg-1", _("Force disabled")),
			("hlg-2", _("Controlled by HDMI"))
		])
		config.av.amlhlg_support.addNotifier(setAMLHLG)
	else:
		config.av.amlhdr10_support = ConfigNothing()
		config.av.amlhlg_support = ConfigNothing()
	hdrType = fileReadLine("/proc/stb/video/hdmi_hdrtype", default=None, source=MODULE_NAME)
	hdrType = hdrType.split() if hdrType else False
	BoxInfo.setItem("havehdmihdrtype", hdrType)
	if hdrType:
		def setHDRType(configElement):
			fileWriteLine("/proc/stb/video/hdmi_hdrtype", configElement.value, source=MODULE_NAME)

		config.av.hdmihdrtype = ConfigSelection(default="auto", choices=[
			("auto", _("Auto")),
			("dolby", "Dolby Vision"),
			("none", "SDR"),
			("hdr10", "HDR10"),
			# ("hdr10+", "HDR10+"),
			("hlg", "HLG")
		])
		config.av.hdmihdrtype.addNotifier(setHDRType)
	else:
		config.av.hdmihdrtype = ConfigNothing()
	hdrSupport = fileReadLine("/proc/stb/hdmi/hlg_support_choices", default=None, source=MODULE_NAME)
	hdrSupport = hdrSupport.split() if hdrSupport else False
	BoxInfo.setItem("HDRSupport", hdrSupport)
	if hdrSupport:
		def setHlgSupport(configElement):
			fileWriteLine("/proc/stb/hdmi/hlg_support", configElement.value, source=MODULE_NAME)

		def setHdr10Support(configElement):
			fileWriteLine("/proc/stb/hdmi/hdr10_support", configElement.value, source=MODULE_NAME)

		def setDisable12Bit(configElement):
			fileWriteLine("/proc/stb/video/disable_12bit", "1" if configElement.value else "0", source=MODULE_NAME)

		def setDisable10Bit(configElement):
			fileWriteLine("/proc/stb/video/disable_10bit", "1" if configElement.value else "0", source=MODULE_NAME)

		config.av.hlg_support = ConfigSelection(default="auto(EDID)", choices=[
			("auto(EDID)", _("Controlled by HDMI")),
			("yes", _("Force enabled")),
			("no", _("Force disabled"))
		])
		config.av.hlg_support.addNotifier(setHlgSupport)
		config.av.hdr10_support = ConfigSelection(default="auto(EDID)", choices=[
			("auto(EDID)", _("Controlled by HDMI")),
			("yes", _("Force enabled")),
			("no", _("Force disabled"))
		])
		config.av.hdr10_support.addNotifier(setHdr10Support)
		config.av.allow_12bit = ConfigYesNo(default=False)
		config.av.allow_12bit.addNotifier(setDisable12Bit)
		config.av.allow_10bit = ConfigYesNo(default=False)
		config.av.allow_10bit.addNotifier(setDisable10Bit)
	audioSource = fileReadLine("/sys/devices/virtual/amhdmitx/amhdmitx0/audio_source" if AMLOGIC else "/proc/stb/hdmi/audio_source", default=None, source=MODULE_NAME)
	audioSource = audioSource.split() if audioSource else False
	BoxInfo.setItem("Canaudiosource", audioSource)
	if audioSource:
		def setAudioSource(configElement):
			fileWriteLine("/sys/devices/virtual/amhdmitx/amhdmitx0/audio_source" if AMLOGIC else "/proc/stb/hdmi/audio_source", configElement.value, source=MODULE_NAME)

		if AMLOGIC:
			config.av.audio_source = ConfigSelection(default="0", choices=[
				("0", "PCM"),
				("1", "S/PDIF"),
				("2", _("Bluetooth"))
			])
		else:
			config.av.audio_source = ConfigSelection(default="pcm", choices=[
				("pcm", "PCM"),
				("spdif", "S/PDIF")
			])
		config.av.audio_source.addNotifier(setAudioSource)
	else:
		config.av.audio_source = ConfigNothing()
	surround = fileReadLine("/proc/stb/audio/3d_surround_choices", default=None, source=MODULE_NAME)
	surround = surround.split() if surround else False
	BoxInfo.setItem("Can3DSurround", surround)
	if surround:
		def set3DSurround(configElement):
			fileWriteLine("/proc/stb/audio/3d_surround", configElement.value, source=MODULE_NAME)

		config.av.surround_3d = ConfigSelection(default="none", choices=[
			("none", _("Off")),
			("hdmi", "HDMI"),
			("spdif", "S/PDIF"),
			("dac", "DAC")
		])
		config.av.surround_3d.addNotifier(set3DSurround)
	else:
		config.av.surround_3d = ConfigNothing()
	surroundSpeaker = fileReadLine("/proc/stb/audio/3d_surround_speaker_position_choices", default=None, source=MODULE_NAME)
	surroundSpeaker = surroundSpeaker.split() if surroundSpeaker else False
	BoxInfo.setItem("Can3DSpeaker", surroundSpeaker)
	if surroundSpeaker:
		def set3DSurroundSpeaker(configElement):
			fileWriteLine("/proc/stb/audio/3d_surround_speaker_position", configElement.value, source=MODULE_NAME)

		config.av.surround_3d_speaker = ConfigSelection(default="center", choices=[
			("center", _("Center")),
			("wide", _("Wide")),
			("extrawide", _("Extra wide"))
		])
		config.av.surround_3d_speaker.addNotifier(set3DSurroundSpeaker)
	else:
		config.av.surround_3d_speaker = ConfigNothing()
	autoVolume = fileReadLine("/proc/stb/audio/avl_choices", default=None, source=MODULE_NAME)
	autoVolume = autoVolume.split() if autoVolume else False
	BoxInfo.setItem("CanAutoVolume", autoVolume)
	if autoVolume:
		def setAutoVolume(configElement):
			fileWriteLine("/proc/stb/audio/avl", configElement.value, source=MODULE_NAME)

		config.av.autovolume = ConfigSelection(default="none", choices=[
			("none", _("Off")),
			("hdmi", "HDMI"),
			("spdif", "S/PDIF"),
			("dac", "DAC")
		])
		config.av.autovolume.addNotifier(setAutoVolume)
	else:
		config.av.autovolume = ConfigNothing()
	multiChannel = access("/proc/stb/audio/multichannel_pcm", W_OK)
	BoxInfo.setItem("HasMultichannelPCM", multiChannel)
	if multiChannel:
		def setPCMMultichannel(configElement):
			fileWriteLine("/proc/stb/audio/multichannel_pcm", configElement.value and "enable" or "disable", source=MODULE_NAME)

		config.av.pcm_multichannel = ConfigYesNo(default=False)
		config.av.pcm_multichannel.addNotifier(setPCMMultichannel)

	if AMLOGIC:
		downmixAC3 = True
		BoxInfo.setItem("CanPcmMultichannel", True)
	else:
		downmixAC3 = fileReadLine("/proc/stb/audio/ac3_choices", default=None, source=MODULE_NAME)
		if downmixAC3:
			downmixAC3 = "downmix" in downmixAC3
		else:
			downmixAC3 = False
			BoxInfo.setItem("CanPcmMultichannel", False)
	BoxInfo.setItem("CanDownmixAC3", downmixAC3)
	if downmixAC3:
		def setAC3Downmix(configElement):
			if AMLOGIC:
				fileWriteLine("/sys/class/audiodsp/digital_raw", configElement.value, source=MODULE_NAME)
			else:
				value = configElement.value and "downmix" or "passthrough"
				if MODEL in ("dm900", "dm920", "dm7080", "dm800"):
					value = configElement.value
				fileWriteLine("/proc/stb/audio/ac3", value, source=MODULE_NAME)

			if BoxInfo.getItem("supportPcmMultichannel", False) and not configElement.value:
				BoxInfo.setItem("CanPcmMultichannel", True)
			else:
				BoxInfo.setItem("CanPcmMultichannel", False)
				if multiChannel:
					config.av.pcm_multichannel.setValue(False)

		if MODEL in ("dm900", "dm920", "dm7080", "dm800"):
			config.av.downmix_ac3 = ConfigSelection(default="downmix", choices=[
				("downmix", _("Downmix")),
				("passthrough", _("Pass-through")),
				("multichannel", _("Convert to multi-channel PCM")),
				("hdmi_best", _("Use best / Controlled by HDMI"))
			])
		elif MODEL in ("dreamone", "dreamtwo"):
			config.av.downmix_ac3 = ConfigSelection(default="0", choices=[
				("0", _("Downmix")),
				("1", _("Pass-through")),
				("2", _("Use best / Controlled by HDMI"))
			])
		else:
			config.av.downmix_ac3 = ConfigYesNo(default=True)
		config.av.downmix_ac3.addNotifier(setAC3Downmix)
	else:
		config.av.downmix_ac3 = ConfigNothing()
	AC3plusTranscode = fileReadLine("/proc/stb/audio/ac3plus_choices", default=None, source=MODULE_NAME)
	AC3plusTranscode = AC3plusTranscode.split() if AC3plusTranscode else False
	BoxInfo.setItem("CanAC3plusTranscode", AC3plusTranscode)
	if AC3plusTranscode:
		def setAC3plusTranscode(configElement):
			fileWriteLine("/proc/stb/audio/ac3plus", configElement.value, source=MODULE_NAME)

		if MODEL in ("dm900", "dm920", "dm7080", "dm800"):
			choiceList = [
					("use_hdmi_caps", _("Controlled by HDMI")),
					("force_ac3", _("Convert to AC3")),
					("multichannel", _("Convert to multi-channel PCM")),
					("hdmi_best", _("Use best / Controlled by HDMI")),
					("force_ddp", _("Force AC3plus"))
				]
		elif MODEL in ("gbquad4k", "gbquad4kpro", "gbue4k", "gbx34k"):
			choiceList = [
					("downmix", _("Downmix")),
					("passthrough", _("Pass-through")),
					("force_ac3", _("Convert to AC3")),
					("multichannel", _("Convert to multi-channel PCM")),
					("force_dts", _("Convert to DTS"))
				]
		else:
			choiceList = [
					("use_hdmi_caps", _("Controlled by HDMI")),
					("force_ac3", _("Convert to AC3"))
				]
		config.av.transcodeac3plus = ConfigSelection(default="force_ac3", choices=choiceList)
		config.av.transcodeac3plus.addNotifier(setAC3plusTranscode)
	dtsHD = fileReadLine("/proc/stb/audio/dtshd_choices", default=None, source=MODULE_NAME)
	dtsHD = dtsHD.split() if dtsHD else False
	BoxInfo.setItem("CanDTSHD", dtsHD)
	if dtsHD:
		def setDTSHD(configElement):
			fileWriteLine("/proc/stb/audio/dtshd", configElement.value, source=MODULE_NAME)

		if MODEL in ("dm7080", "dm820"):
			default = "use_hdmi_caps"
			choiceList = [
				("use_hdmi_caps", _("Controlled by HDMI")),
				("force_dts", _("Convert to DTS"))
			]
		else:
			default = "downmix"
			choiceList = [
				("downmix", _("Downmix")),
				("force_dts", _("Convert to DTS")),
				("use_hdmi_caps", _("Controlled by HDMI")),
				("multichannel", _("Convert to multi-channel PCM")),
				("hdmi_best", _("Use best / Controlled by HDMI"))
			]
		config.av.dtshd = ConfigSelection(default=default, choices=choiceList)
		config.av.dtshd.addNotifier(setDTSHD)
	wmaPro = fileReadLine("/proc/stb/audio/wmapro_choices", default=None, source=MODULE_NAME)
	wmaPro = wmaPro.split() if wmaPro else False
	BoxInfo.setItem("CanWMAPRO", wmaPro)
	if wmaPro:
		def setWMAPro(configElement):
			fileWriteLine("/proc/stb/audio/wmapro", configElement.value, source=MODULE_NAME)

		config.av.wmapro = ConfigSelection(default="downmix", choices=[
			("downmix", _("Downmix")),
			("passthrough", _("Pass-through")),
			("multichannel", _("Convert to multi-channel PCM")),
			("hdmi_best", _("Use best / Controlled by HDMI"))
		])
		config.av.wmapro.addNotifier(setWMAPro)
	dtsDownmix = fileReadLine("/proc/stb/audio/dts_choices", default=None, source=MODULE_NAME)
	dtsDownmix = "downmix" in dtsDownmix if dtsDownmix else False
	BoxInfo.setItem("CanDownmixDTS", dtsDownmix)
	if dtsDownmix:
		def setDTSDownmix(configElement):
			fileWriteLine("/proc/stb/audio/dts", configElement.value and "downmix" or "passthrough", source=MODULE_NAME)

		config.av.downmix_dts = ConfigYesNo(default=True)
		config.av.downmix_dts.addNotifier(setDTSDownmix)
	aacDownmix = fileReadLine("/proc/stb/audio/aac_choices", default=None, source=MODULE_NAME)
	aacDownmix = "downmix" in aacDownmix if aacDownmix else False
	BoxInfo.setItem("CanDownmixAAC", aacDownmix)
	if aacDownmix:
		def setAACDownmix(configElement):
			value = configElement.value if MODEL in ("dm900", "dm920", "dm7080", "dm800", "gbquad4k", "gbquad4kpro", "gbue4k", "gbx34k") else configElement.value and "downmix" or "passthrough"
			fileWriteLine("/proc/stb/audio/aac", value, source=MODULE_NAME)

		if MODEL in ("dm900", "dm920", "dm7080", "dm800"):
			config.av.downmix_aac = ConfigSelection(default="downmix", choices=[
				("downmix", _("Downmix")),
				("passthrough", _("Pass-through")),
				("multichannel", _("Convert to multi-channel PCM")),
				("hdmi_best", _("Use best / Controlled by HDMI"))
			])
		elif MODEL in ("gbquad4k", "gbquad4kpro", "gbue4k", "gbx34k"):
			config.av.downmix_aac = ConfigSelection(default="downmix", choices=[
				("downmix", _("Downmix")),
				("passthrough", _("Pass-through")),
				("multichannel", _("Convert to multi-channel PCM")),
				("force_ac3", _("Convert to AC3")),
				("force_dts", _("Convert to DTS")),
				("use_hdmi_cacenter", _("Use best / Controlled by HDMI")),
				("wide", _("Wide")),
				("extrawide", _("Extra wide"))
			])
		else:
			config.av.downmix_aac = ConfigYesNo(default=True)
		config.av.downmix_aac.addNotifier(setAACDownmix)
	aacplusDownmix = fileReadLine("/proc/stb/audio/aacplus_choices", default=None, source=MODULE_NAME)
	aacplusDownmix = "downmix" in aacplusDownmix if aacplusDownmix else False
	BoxInfo.setItem("CanDownmixAACPlus", aacplusDownmix)
	if aacplusDownmix:
		def setAACDownmixPlus(configElement):
			fileWriteLine("/proc/stb/audio/aacplus", configElement.value, source=MODULE_NAME)

		config.av.downmix_aacplus = ConfigSelection(default="downmix", choices=[
			("downmix", _("Downmix")),
			("passthrough", _("Pass-through")),
			("multichannel", _("Convert to multi-channel PCM")),
			("force_ac3", _("Convert to AC3")),
			("force_dts", _("Convert to DTS")),
			("use_hdmi_cacenter", _("Use best / Controlled by HDMI")),
			("wide", _("Wide")),
			("extrawide", _("Extra wide"))
		])
		config.av.downmix_aacplus.addNotifier(setAACDownmixPlus)
	if exists("/proc/stb/audio/aac_transcode_choices"):
		aacTranscodeAll = [
			("off", _("Off")),
			("ac3", "AC3"),
			("dts", "DTS")
		]
		# The translation text must look exactly like the read value. It is then adjusted with the PO file.
		aactranscodeChoices = fileReadLine("/proc/stb/audio/aac_transcode_choices", default=None, source=MODULE_NAME)
		aactranscodeChoices = aactranscodeChoices.split() if aactranscodeChoices else []
		aacTranscode = [(x[0], x[1]) for x in aacTranscodeAll if x[0] in aactranscodeChoices]
		default = aacTranscode[0][0] if aacTranscode else "off"
		print(f"[AVSwitch] aactranscodeChoices choices={aactranscodeChoices}, default={default}.")
	else:
		aacTranscode = False
	if BoxInfo.getItem("CanAudioDelay"):
		def setAudioDelay(configElement):
			try:
				open("/proc/stb/audio/audio_delay_pcm", "w").write(format(configElement.value * 90, "x"))
			except:
				open("/proc/stb/audio/audio_delay_bitstream", "w").write(format(configElement.value * 90, "x"))
		config.av.audiodelay = ConfigSelectionNumber(-1000, 1000, 5, default=0)
		config.av.audiodelay.addNotifier(setAudioDelay)
	else:
		config.av.audiodelay = ConfigNothing()
	BoxInfo.setItem("CanAACTranscode", aacTranscode)
	if aacTranscode:
		def setAACTranscode(configElement):
			fileWriteLine("/proc/stb/audio/aac_transcode", configElement.value, source=MODULE_NAME)

		config.av.transcodeaac = ConfigSelection(default=default, choices=aacTranscode)
		config.av.transcodeaac.addNotifier(setAACTranscode)
	else:
		config.av.transcodeaac = ConfigNothing()
	btAudio = fileReadLine("/proc/stb/audio/btaudio", default=None, source=MODULE_NAME)
	btAudio = btAudio.split() if btAudio else False
	BoxInfo.setItem("CanBTAudio", btAudio)
	if btAudio:
		def setBTAudio(configElement):
			fileWriteLine("/proc/stb/audio/btaudio", "on" if configElement.value else "off", source=MODULE_NAME)

		config.av.btaudio = ConfigOnOff(default=False)
		config.av.btaudio.addNotifier(setBTAudio)
	else:
		config.av.btaudio = ConfigNothing()
	btAudioDelay = fileReadLine("/proc/stb/audio/btaudio_delay", default=None, source=MODULE_NAME)
	btAudioDelay = btAudioDelay.split() if btAudioDelay else False
	BoxInfo.setItem("CanBTAudioDelay", btAudioDelay)
	if btAudioDelay:
		def setBTAudioDelay(configElement):
			fileWriteLine("/proc/stb/audio/btaudio_delay", format(configElement.value * 90, "x"), source=MODULE_NAME)

		config.av.btaudiodelay = ConfigSelectionNumber(min=-1000, max=1000, stepwidth=5, default=0)
		config.av.btaudiodelay.addNotifier(setBTAudioDelay)
	else:
		config.av.btaudiodelay = ConfigNothing()
	if exists("/proc/stb/vmpeg/0/pep_scaler_sharpness"):
		def setScalerSharpness(configElement):
			error = False
			if not fileWriteLine("/proc/stb/vmpeg/0/pep_scaler_sharpness", f"{configElement.value:08X}\n", source=MODULE_NAME):
				error = True
			if not error and not fileWriteLine("/proc/stb/vmpeg/0/pep_apply", "1", source=MODULE_NAME):
				error = True
			if error:
				print(f"[AVSwitch] Setting scaler sharpness to '{configElement.value:08X}' failed!")
			else:
				print(f"[AVSwitch] Setting scaler sharpness to '{configElement.value:08X}'.")

		default = 5 if MODEL in ("gbquad", "gbquadplus") else 13
		config.av.scaler_sharpness = ConfigSlider(default=default, limits=(0, 26))
		config.av.scaler_sharpness.addNotifier(setScalerSharpness)
	else:
		config.av.scaler_sharpness = NoSave(ConfigNothing())

	config.av.force = ConfigSelection(default=None, choices=[
		(None, _("Do not force")),
		("50", _("Force 50Hz")),
		("60", _("Force 60Hz"))
	])


avSwitch = AVSwitch()
iAVSwitch = avSwitch
