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
    "enable_app_voices": "boolean(default=False)",
    "enable_multi_voices": "boolean(default=False)",
    "voices_per_slot": "integer(min=1, max=10, default=3)"
}

script_category = "VoiceSwitcher"

class VoiceSwitcherSettingsPanel(SettingsPanel):
    title = "VoiceSwitcher"
    
    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        
        self.enableAppVoicesCb = sHelper.addItem(wx.CheckBox(self, label="Enable application specific voices"))
        self.enableAppVoicesCb.SetValue(config.conf["VoiceSwitcher"]["enable_app_voices"])
        self.enableAppVoicesCb.Bind(wx.EVT_CHECKBOX, self.onToggleAppVoices)

        # Chức năng sử dụng nhiều giọng nói cho một vị trí
        self.enableMultiCb = sHelper.addItem(wx.CheckBox(self, label="Enable multiple voices per slot"))
        self.enableMultiCb.SetValue(config.conf["VoiceSwitcher"]["enable_multi_voices"])
        self.enableMultiCb.Bind(wx.EVT_CHECKBOX, self.onToggleMulti)

        self.multiSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lblMulti = wx.StaticText(self, label="Voices per slot (1-10):")
        self.multiSizer.Add(self.lblMulti, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        
        # Combobox có thể nhập được (CB_DROPDOWN)
        self.voicesPerSlotCombo = wx.ComboBox(self, choices=[str(i) for i in range(1, 11)], style=wx.CB_DROPDOWN)
        self.voicesPerSlotCombo.SetValue(str(config.conf["VoiceSwitcher"]["voices_per_slot"]))
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
        self.app_keys = []
        plugin = GlobalPlugin.instance
        if plugin and "apps" in plugin.data:
            for window_id, cfg in plugin.data["apps"].items():
                window_title = cfg.get('window_title', window_id)
                display_name = cfg.get('display_name', cfg.get('name', 'Unknown'))
                
                item_text = f"{window_title}  ->  {display_name}"
                self.appVoicesList.Append(item_text)
                self.app_keys.append(window_id)

    def updateVisibility(self):
        is_app_enabled = self.enableAppVoicesCb.GetValue()
        has_items = len(self.app_keys) > 0
        should_show_app = is_app_enabled and has_items
        
        self.lblList.Show(should_show_app)
        self.appVoicesList.Show(should_show_app)
        self.btnRemove.Show(should_show_app)
        self.btnRemoveAll.Show(should_show_app)

        is_multi_enabled = self.enableMultiCb.GetValue()
        self.lblMulti.Show(is_multi_enabled)
        self.voicesPerSlotCombo.Show(is_multi_enabled)

        self.Layout()

    def onToggleAppVoices(self, evt):
        self.updateVisibility()

    def onToggleMulti(self, evt):
        self.updateVisibility()

    def onRemove(self, evt):
        selection = self.appVoicesList.GetSelection()
        if selection != wx.NOT_FOUND:
            window_id = self.app_keys[selection]
            plugin = GlobalPlugin.instance
            if plugin and "apps" in plugin.data and window_id in plugin.data["apps"]:
                del plugin.data["apps"][window_id]
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
        config.conf["VoiceSwitcher"]["enable_app_voices"] = self.enableAppVoicesCb.GetValue()
        config.conf["VoiceSwitcher"]["enable_multi_voices"] = self.enableMultiCb.GetValue()
        try:
            val = int(self.voicesPerSlotCombo.GetValue())
            if val < 1: val = 1
            if val > 10: val = 10
            config.conf["VoiceSwitcher"]["voices_per_slot"] = val
        except ValueError:
            pass


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    instance = None 
    
    def __init__(self, *args, **kwargs):
        super(GlobalPlugin, self).__init__(*args, **kwargs)
        GlobalPlugin.instance = self
        self.data = {"slots": {}, "apps": {}}
        self.slot = None
        self.last_window_id = None
        
        self.save_timer = None
        self.slot_timer = None 
        self.pending_slot = None
        self.pending_sub_slot = 1
        
        self.load()
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(VoiceSwitcherSettingsPanel)

    def terminate(self):
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(VoiceSwitcherSettingsPanel)
        except ValueError:
            pass
        if self.save_timer and self.save_timer.IsRunning():
            self.save_timer.Stop()
        if self.slot_timer and self.slot_timer.IsRunning():
            self.slot_timer.Stop()
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
                loaded_data = pickle.load(f)
                if "slots" in loaded_data and "apps" in loaded_data:
                    self.data = loaded_data
                else:
                    self.data["slots"] = loaded_data
        except Exception:
            self.data = {"slots": {}, "apps": {}}

    def _applySynthConfig(self, config_dict, announce=False):
        if not config_dict or 'name' not in config_dict:
            return False
        try:
            synthDriverHandler.setSynth(config_dict['name'])
            synth = synthDriverHandler.getSynth()
            for param in ['voice', 'variant', 'rate', 'volume', 'pitch']:
                if param in config_dict:
                    try:
                        if getattr(synth, param) != config_dict[param]:
                            if param == 'voice':
                                synthDriverHandler.changeVoice(synth, config_dict['voice'])
                            else:
                                setattr(synth, param, config_dict[param])
                    except (NotImplementedError, AttributeError):
                        pass
            if announce:
                try:
                    if synth.name == "silence":
                        ui.message("Silence")
                    else:
                        voice_id = synth.voice
                        ui.message(synth.availableVoices[voice_id].displayName)
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
        if config.conf["VoiceSwitcher"]["enable_app_voices"]:
            try:
                app_name = obj.appModule.appModuleName if hasattr(obj, 'appModule') and obj.appModule else "unknown"
                window_class = obj.windowClassName if hasattr(obj, 'windowClassName') else "unknown"
                window_id = f"{app_name}_{window_class}"

                if window_id != self.last_window_id:
                    self.last_window_id = window_id
                    
                    if window_id in self.data["apps"]:
                        saved_cfg = self.data["apps"][window_id]
                        synth = synthDriverHandler.getSynth()
                        curr_name = synth.name
                        curr_voice = getattr(synth, 'voice', None)
                        
                        if curr_name != saved_cfg.get('name') or curr_voice != saved_cfg.get('voice'):
                            self._applySynthConfig(saved_cfg, announce=False)
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
            except (NotImplementedError, AttributeError): pass
            
        self.data["slots"][self.slot] = cfg
        self.write()
        ui.message(f"Slot {self.slot} saved.")

    def _handleDoublePress(self):
        if not config.conf["VoiceSwitcher"]["enable_app_voices"]:
            ui.message("App voices disabled.")
            return

        fg = api.getForegroundObject()
        if not fg:
            ui.message("No window found.")
            return
            
        app_name = fg.appModule.appModuleName if hasattr(fg, 'appModule') and fg.appModule else "unknown"
        window_class = fg.windowClassName if hasattr(fg, 'windowClassName') else "unknown"
        window_id = f"{app_name}_{window_class}"
        
        friendly_title = fg.name if fg.name else app_name
        
        if window_id in self.data["apps"]:
            del self.data["apps"][window_id]
            self.write()
            ui.message("Window voice removed.")
        else:
            synth = synthDriverHandler.getSynth()
            cfg = {'name': synth.name}
            for param in ['voice', 'variant', 'rate', 'volume', 'pitch']:
                try: cfg[param] = getattr(synth, param)
                except (NotImplementedError, AttributeError): pass
            
            try:
                if synth.name == "silence":
                    cfg['display_name'] = "Silence"
                else:
                    voice_id = synth.voice
                    cfg['display_name'] = synth.availableVoices[voice_id].displayName
            except Exception:
                cfg['display_name'] = synth.description
                
            cfg['window_title'] = friendly_title 
                
            self.data["apps"][window_id] = cfg
            self.write()
            ui.message("Window voice saved.")

    @script(description="Save to slot (single press) or Add/Remove app voice (double press).", category=script_category)
    def script_saveSynth(self, gesture):
        repeat_count = scriptHandler.getLastScriptRepeatCount()
        
        if repeat_count == 0:
            if self.save_timer and self.save_timer.IsRunning():
                self.save_timer.Stop()
            self.save_timer = wx.CallLater(300, self._handleSinglePress)
        elif repeat_count == 1:
            if self.save_timer and self.save_timer.IsRunning():
                self.save_timer.Stop()
            self._handleDoublePress()

    # --- CÁC SCRIPT CHỌN SLOT & CHUYỂN GIỌNG ---
    def _handleSlotTimer(self):
        # Tính toán ID slot sau 300ms kể từ lần nhấn cuối
        if config.conf["VoiceSwitcher"]["enable_multi_voices"]:
            max_voices = config.conf["VoiceSwitcher"]["voices_per_slot"]
            sub_slot = min(self.pending_sub_slot, max_voices)
            
            if sub_slot == 1:
                # Giữ nguyên số nguyên 1, 2, 3... cho lần nhấn đầu (tương thích ngược với các slot cũ)
                self.slot = self.pending_slot
            else:
                # Sử dụng chuỗi dạng "1.2", "1.3"... cho các lần nhấn tiếp theo
                self.slot = f"{self.pending_slot}.{sub_slot}"
        else:
            self.slot = self.pending_slot
            
        self._setSynthForSlot()

    def _processSlotPress(self, slot_num):
        repeat_count = scriptHandler.getLastScriptRepeatCount()
        
        if self.slot_timer and self.slot_timer.IsRunning():
            self.slot_timer.Stop()
            
        self.pending_slot = slot_num
        self.pending_sub_slot = repeat_count + 1
        
        # Chờ 300ms để xem người dùng có nhấn tiếp hay không
        self.slot_timer = wx.CallLater(300, self._handleSlotTimer)

    @script(description="Set or select synthesizer for slot 1.", category=script_category)
    def script_setSynth1(self, gesture): self._processSlotPress(1)
    @script(description="Set or select synthesizer for slot 2.", category=script_category)
    def script_setSynth2(self, gesture): self._processSlotPress(2)
    @script(description="Set or select synthesizer for slot 3.", category=script_category)
    def script_setSynth3(self, gesture): self._processSlotPress(3)
    @script(description="Set or select synthesizer for slot 4.", category=script_category)
    def script_setSynth4(self, gesture): self._processSlotPress(4)
    @script(description="Set or select synthesizer for slot 5.", category=script_category)
    def script_setSynth5(self, gesture): self._processSlotPress(5)
    @script(description="Set or select synthesizer for slot 6.", category=script_category)
    def script_setSynth6(self, gesture): self._processSlotPress(6)
    @script(description="Set or select synthesizer for slot 7.", category=script_category)
    def script_setSynth7(self, gesture): self._processSlotPress(7)
    @script(description="Set or select synthesizer for slot 8.", category=script_category)
    def script_setSynth8(self, gesture): self._processSlotPress(8)
    @script(description="Set or select synthesizer for slot 9.", category=script_category)
    def script_setSynth9(self, gesture): self._processSlotPress(9)
    @script(description="Set or select synthesizer for slot 0.", category=script_category)
    def script_setSynth0(self, gesture): self._processSlotPress(0)

    @script(description="Toggle between voice slot 1 and 2.", category=script_category)
    def script_toggleSynth1And2(self, gesture):
        slots = self.data["slots"]
        if 1 not in slots or 2 not in slots:
            ui.message("Slot 1 or 2 empty.")
            return
            
        synth = synthDriverHandler.getSynth()
        curr_name = synth.name
        curr_voice = getattr(synth, 'voice', None)
        
        if slots[1].get('name') == curr_name and slots[1].get('voice') == curr_voice:
            self.slot = 2
        else:
            self.slot = 1
            
        self._applySynthConfig(slots[self.slot], announce=True)

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
    }