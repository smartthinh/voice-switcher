# -*- coding: utf-8 -*-
"""
Voice Slots Manager
"""

import os
import pickle
import globalPluginHandler
import synthDriverHandler
import ui
import api
import scriptHandler
import config
import gui
import wx
from gui.settingsDialogs import SettingsPanel
from scriptHandler import script

# Configure config spec for the settings panel
config.conf.spec["VoiceSwitcher"] = {
	"enableAppVoices": "boolean(default=False)",
	"enableMultiVoices": "boolean(default=False)",
	"voicesPerSlot": "integer(min=1, max=10, default=3)"
}

scriptCategory = "VoiceSwitcher"

class VoiceSwitcherSettingsPanel(SettingsPanel):
	title = "VoiceSwitcher"
	
	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		
		self.enableAppVoicesCb = sHelper.addItem(wx.CheckBox(self, label="Enable application specific voices"))
		self.enableAppVoicesCb.SetValue(config.conf["VoiceSwitcher"]["enableAppVoices"])
		self.enableAppVoicesCb.Bind(wx.EVT_CHECKBOX, self.onToggleAppVoices)

		# Chức năng sử dụng nhiều giọng nói cho một vị trí
		self.enableMultiCb = sHelper.addItem(wx.CheckBox(self, label="Enable multiple voices per slot"))
		self.enableMultiCb.SetValue(config.conf["VoiceSwitcher"]["enableMultiVoices"])
		self.enableMultiCb.Bind(wx.EVT_CHECKBOX, self.onToggleMulti)

		self.multiSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.lblMulti = wx.StaticText(self, label="Voices per slot (1-10):")
		self.multiSizer.Add(self.lblMulti, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
		
		# Combobox có thể nhập được (CB_DROPDOWN)
		self.voicesPerSlotCombo = wx.ComboBox(self, choices=[str(i) for i in range(1, 11)], style=wx.CB_DROPDOWN)
		self.voicesPerSlotCombo.SetValue(str(config.conf["VoiceSwitcher"]["voicesPerSlot"]))
		self.multiSizer.Add(self.voicesPerSlotCombo, 0, 0, 0)
		sHelper.addItem(self.multiSizer)

		self.lblList = wx.StaticText(self, label="Saved window voices:")
		settingsSizer.Add(self.lblList, 0, wx.TOP, 5)
		
		self.appVoicesList = wx.ListBox(self, choices=[])
		settingsSizer.Add(self.appVoicesList, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
		
		self.btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.btnRemove = wx.Button(self, label="Remove")
		self.btnRemove.Bind(wx.EVT_BUTTON, self.onRemove)
		self.btnSizer.Add(self.btnRemove, 0, wx.RIGHT, 5)
		
		self.btnRemoveAll = wx.Button(self, label="Remove All")
		self.btnRemoveAll.Bind(wx.EVT_BUTTON, self.onRemoveAll)
		self.btnSizer.Add(self.btnRemoveAll, 0, 0, 0)
		
		settingsSizer.Add(self.btnSizer, 0, wx.BOTTOM, 5)

		self.populateList()
		self.updateVisibility()

	def populateList(self):
		self.appVoicesList.Clear()
		self.appKeys = []
		plugin = GlobalPlugin.instance
		if plugin and "apps" in plugin.data:
			for windowId, cfg in plugin.data["apps"].items():
				windowTitle = cfg.get('windowTitle', windowId)
				displayName = cfg.get('displayName', cfg.get('name', 'Unknown'))
				
				itemText = f"{windowTitle}  ->  {displayName}"
				self.appVoicesList.Append(itemText)
				self.appKeys.append(windowId)

	def updateVisibility(self):
		isAppEnabled = self.enableAppVoicesCb.GetValue()
		hasItems = len(self.appKeys) > 0
		shouldShowApp = isAppEnabled and hasItems
		
		self.lblList.Show(shouldShowApp)
		self.appVoicesList.Show(shouldShowApp)
		self.btnRemove.Show(shouldShowApp)
		self.btnRemoveAll.Show(shouldShowApp)

		isMultiEnabled = self.enableMultiCb.GetValue()
		self.lblMulti.Show(isMultiEnabled)
		self.voicesPerSlotCombo.Show(isMultiEnabled)

		self.Layout()

	def onToggleAppVoices(self, evt):
		self.updateVisibility()

	def onToggleMulti(self, evt):
		self.updateVisibility()

	def onRemove(self, evt):
		selection = self.appVoicesList.GetSelection()
		if selection != wx.NOT_FOUND:
			windowId = self.appKeys[selection]
			plugin = GlobalPlugin.instance
			if plugin and "apps" in plugin.data and windowId in plugin.data["apps"]:
				del plugin.data["apps"][windowId]
				plugin.write()
				self.populateList()
				self.updateVisibility()
				self.appVoicesList.SetFocus()

	def onRemoveAll(self, evt):
		plugin = GlobalPlugin.instance
		if plugin:
			plugin.data["apps"].clear()
			plugin.write()
			self.populateList()
			self.updateVisibility()

	def onSave(self):
		config.conf["VoiceSwitcher"]["enableAppVoices"] = self.enableAppVoicesCb.GetValue()
		config.conf["VoiceSwitcher"]["enableMultiVoices"] = self.enableMultiCb.GetValue()
		try:
			val = int(self.voicesPerSlotCombo.GetValue())
			if val < 1: val = 1
			if val > 10: val = 10
			config.conf["VoiceSwitcher"]["voicesPerSlot"] = val
		except ValueError:
			pass


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	instance = None 
	
	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		GlobalPlugin.instance = self
		self.data = {"slots": {}, "apps": {}}
		self.slot = None
		self.lastWindowId = None
		
		self.saveTimer = None
		self.slotTimer = None 
		self.pendingSlot = None
		self.pendingSubSlot = 1
		
		self.load()
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(VoiceSwitcherSettingsPanel)

	def terminate(self):
		try:
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(VoiceSwitcherSettingsPanel)
		except ValueError:
			pass
		if self.saveTimer and self.saveTimer.IsRunning():
			self.saveTimer.Stop()
		if self.slotTimer and self.slotTimer.IsRunning():
			self.slotTimer.Stop()
		GlobalPlugin.instance = None
		super(GlobalPlugin, self).terminate()

	def write(self):
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_slots.dat")
		try:
			with open(path, 'wb') as f:
				pickle.dump(self.data, f)
		except (IOError, OSError):
			ui.message("Save error.")

	def load(self):
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_slots.dat")
		if not os.path.exists(path): 
			return
		try:
			with open(path, 'rb') as f:
				loadedData = pickle.load(f)
				if "slots" in loadedData and "apps" in loadedData:
					self.data = loadedData
				else:
					self.data["slots"] = loadedData
		except Exception:
			self.data = {"slots": {}, "apps": {}}

	def _applySynthConfig(self, configDict, announce=False):
		if not configDict or 'name' not in configDict:
			return False
		try:
			synthDriverHandler.setSynth(configDict['name'])
			synth = synthDriverHandler.getSynth()
			for param in ['voice', 'variant', 'rate', 'volume', 'pitch']:
				if param in configDict:
					try:
						if getattr(synth, param) != configDict[param]:
							if param == 'voice':
								synthDriverHandler.changeVoice(synth, configDict['voice'])
							else:
								setattr(synth, param, configDict[param])
					except Exception:
						pass
			if announce:
				try:
					if synth.name == "silence":
						ui.message("Silence")
					else:
						voiceId = synth.voice
						ui.message(synth.availableVoices[voiceId].displayName)
				except Exception:
					ui.message(synth.description)
			return True
		except Exception:
			return False

	def _setSynthForSlot(self):
		if self.slot in self.data["slots"]:
			self._applySynthConfig(self.data["slots"][self.slot], announce=True)
		else:
			ui.message(f"Slot {self.slot} empty.")

	def event_foreground(self, obj, nextHandler):
		if config.conf["VoiceSwitcher"]["enableAppVoices"]:
			try:
				appName = obj.appModule.appModuleName if hasattr(obj, 'appModule') and obj.appModule else "unknown"
				windowClass = obj.windowClassName if hasattr(obj, 'windowClassName') else "unknown"
				windowId = f"{appName}_{windowClass}"

				if windowId != self.lastWindowId:
					self.lastWindowId = windowId
					
					if windowId in self.data["apps"]:
						savedCfg = self.data["apps"][windowId]
						synth = synthDriverHandler.getSynth()
						currName = synth.name
						currVoice = getattr(synth, 'voice', None)
						
						if currName != savedCfg.get('name') or currVoice != savedCfg.get('voice'):
							self._applySynthConfig(savedCfg, announce=False)
			except Exception:
				pass
		nextHandler()

	def _handleSinglePress(self):
		if self.slot is None:
			ui.message("No slot selected.")
			return

		synth = synthDriverHandler.getSynth()
		cfg = {'name': synth.name}
		for param in ['voice', 'variant', 'rate', 'volume', 'pitch']:
			try: cfg[param] = getattr(synth, param)
			except Exception: pass
			
		self.data["slots"][self.slot] = cfg
		self.write()
		ui.message(f"Slot {self.slot} saved.")

	def _handleDoublePress(self):
		if not config.conf["VoiceSwitcher"]["enableAppVoices"]:
			ui.message("App voices disabled.")
			return

		fg = api.getForegroundObject()
		if not fg:
			ui.message("No window found.")
			return
			
		appName = fg.appModule.appModuleName if hasattr(fg, 'appModule') and fg.appModule else "unknown"
		windowClass = fg.windowClassName if hasattr(fg, 'windowClassName') else "unknown"
		windowId = f"{appName}_{windowClass}"
		
		friendlyTitle = fg.name if fg.name else appName
		
		if windowId in self.data["apps"]:
			del self.data["apps"][windowId]
			self.write()
			ui.message("Window voice removed.")
		else:
			synth = synthDriverHandler.getSynth()
			cfg = {'name': synth.name}
			for param in ['voice', 'variant', 'rate', 'volume', 'pitch']:
				try: cfg[param] = getattr(synth, param)
				except Exception: pass
			
			try:
				if synth.name == "silence":
					cfg['displayName'] = "Silence"
				else:
					voiceId = synth.voice
					cfg['displayName'] = synth.availableVoices[voiceId].displayName
			except Exception:
				cfg['displayName'] = synth.description
				
			cfg['windowTitle'] = friendlyTitle 
				
			self.data["apps"][windowId] = cfg
			self.write()
			ui.message("Window voice saved.")

	@script(description="Save to slot (single press) or Add/Remove app voice (double press).", category=scriptCategory)
	def script_saveSynth(self, gesture):
		repeatCount = scriptHandler.getLastScriptRepeatCount()
		
		if repeatCount == 0:
			if self.saveTimer and self.saveTimer.IsRunning():
				self.saveTimer.Stop()
			self.saveTimer = wx.CallLater(300, self._handleSinglePress)
		elif repeatCount == 1:
			if self.saveTimer and self.saveTimer.IsRunning():
				self.saveTimer.Stop()
			self._handleDoublePress()

	# --- CÁC SCRIPT CHỌN SLOT & CHUYỂN GIỌNG ---
	def _handleSlotTimer(self):
		# Tính toán ID slot sau 300ms kể từ lần nhấn cuối
		if config.conf["VoiceSwitcher"]["enableMultiVoices"]:
			maxVoices = config.conf["VoiceSwitcher"]["voicesPerSlot"]
			subSlot = min(self.pendingSubSlot, maxVoices)
			
			if subSlot == 1:
				# Giữ nguyên số nguyên 1, 2, 3... cho lần nhấn đầu (tương thích ngược với các slot cũ)
				self.slot = self.pendingSlot
			else:
				# Sử dụng chuỗi dạng "1.2", "1.3"... cho các lần nhấn tiếp theo
				self.slot = f"{self.pendingSlot}.{subSlot}"
		else:
			self.slot = self.pendingSlot
			
		self._setSynthForSlot()

	def _processSlotPress(self, slotNum):
		repeatCount = scriptHandler.getLastScriptRepeatCount()
		
		if self.slotTimer and self.slotTimer.IsRunning():
			self.slotTimer.Stop()
			
		self.pendingSlot = slotNum
		self.pendingSubSlot = repeatCount + 1
		
		# Chờ 300ms để xem người dùng có nhấn tiếp hay không
		self.slotTimer = wx.CallLater(300, self._handleSlotTimer)

	@script(description="Set or select synthesizer for slot 1.", category=scriptCategory)
	def script_setSynth1(self, gesture): self._processSlotPress(1)
	@script(description="Set or select synthesizer for slot 2.", category=scriptCategory)
	def script_setSynth2(self, gesture): self._processSlotPress(2)
	@script(description="Set or select synthesizer for slot 3.", category=scriptCategory)
	def script_setSynth3(self, gesture): self._processSlotPress(3)
	@script(description="Set or select synthesizer for slot 4.", category=scriptCategory)
	def script_setSynth4(self, gesture): self._processSlotPress(4)
	@script(description="Set or select synthesizer for slot 5.", category=scriptCategory)
	def script_setSynth5(self, gesture): self._processSlotPress(5)
	@script(description="Set or select synthesizer for slot 6.", category=scriptCategory)
	def script_setSynth6(self, gesture): self._processSlotPress(6)
	@script(description="Set or select synthesizer for slot 7.", category=scriptCategory)
	def script_setSynth7(self, gesture): self._processSlotPress(7)
	@script(description="Set or select synthesizer for slot 8.", category=scriptCategory)
	def script_setSynth8(self, gesture): self._processSlotPress(8)
	@script(description="Set or select synthesizer for slot 9.", category=scriptCategory)
	def script_setSynth9(self, gesture): self._processSlotPress(9)
	@script(description="Set or select synthesizer for slot 0.", category=scriptCategory)
	def script_setSynth0(self, gesture): self._processSlotPress(0)

	@script(description="Toggle between voice slot 1 and 2.", category=scriptCategory)
	def script_toggleSynth1And2(self, gesture):
		slots = self.data["slots"]
		if 1 not in slots or 2 not in slots:
			ui.message("Slot 1 or 2 empty.")
			return
			
		synth = synthDriverHandler.getSynth()
		currName = synth.name
		currVoice = getattr(synth, 'voice', None)
		
		if slots[1].get('name') == currName and slots[1].get('voice') == currVoice:
			self.slot = 2
		else:
			self.slot = 1
			
		self._applySynthConfig(slots[self.slot], announce=True)

	@script(description="Toggle application specific voices.", category=scriptCategory)
	def script_toggleAppVoices(self, gesture):
		config.conf["VoiceSwitcher"]["enableAppVoices"] = not config.conf["VoiceSwitcher"]["enableAppVoices"]
		state = "enabled" if config.conf["VoiceSwitcher"]["enableAppVoices"] else "disabled"
		ui.message(f"App voices {state}")

	@script(description="Toggle multiple voices per slot.", category=scriptCategory)
	def script_toggleMultiVoices(self, gesture):
		config.conf["VoiceSwitcher"]["enableMultiVoices"] = not config.conf["VoiceSwitcher"]["enableMultiVoices"]
		state = "enabled" if config.conf["VoiceSwitcher"]["enableMultiVoices"] else "disabled"
		ui.message(f"Multi voices {state}")

	__gestures = {
		"kb:NVDA+control+shift+1": "setSynth1",
		"kb:NVDA+control+shift+2": "setSynth2",
		"kb:NVDA+control+shift+3": "setSynth3",
		"kb:NVDA+control+shift+4": "setSynth4",
		"kb:NVDA+control+shift+5": "setSynth5",
		"kb:NVDA+control+shift+6": "setSynth6",
		"kb:NVDA+control+shift+7": "setSynth7",
		"kb:NVDA+control+shift+8": "setSynth8",
		"kb:NVDA+control+shift+9": "setSynth9",
		"kb:NVDA+control+shift+0": "setSynth0",
		"kb:`": "toggleSynth1And2",
		"kb:NVDA+control+shift+s": "saveSynth",
		"kb:NVDA+control+shift+a": "toggleAppVoices",
		"kb:NVDA+control+shift+p": "toggleMultiVoices",
	}