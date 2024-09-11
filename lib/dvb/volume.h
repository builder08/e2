#ifndef __volume_h
#define __volume_h

#ifdef DREAMNEXTGEN
#ifdef HAVE_ALSA
#undef HAVE_ALSA
#endif
#endif

#ifdef HAVE_ALSA
#include <alsa/asoundlib.h>
#endif

#include <lib/base/ebase.h>

class eDVBVolumecontrol
{
private:
#ifdef HAVE_ALSA
	snd_mixer_elem_t *mainVolume;
	snd_mixer_t *alsaMixerHandle;
#endif
	static eDVBVolumecontrol *instance;
	eDVBVolumecontrol();
#ifdef SWIG
	~eDVBVolumecontrol();
#endif
	int openMixer();
	void closeMixer(int fd);

	bool muted;
	int leftVol, rightVol;
	int m_volsteps;

	int checkVolume(int vol);

public:
	static eDVBVolumecontrol *getInstance();

	void setVolumeSteps(int steps) { m_volsteps = steps; }
	int volumeUp(int left = 0, int right = 0);
	int volumeDown(int left = 0, int right = 0);

	int setVolume(int left, int right);

	void volumeMute();
	void volumeUnMute();
	void volumeToggleMute();

	int getVolume() { return leftVol; }
	int getVolumeLeft() { return leftVol; }
	int getVolumeRight() { return rightVol; }
	bool isMuted() { return muted; }
};

#endif //__volume_h
