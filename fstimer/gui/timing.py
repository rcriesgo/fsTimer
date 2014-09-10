#fsTimer - free, open source software for race timing.
#Copyright 2012-14 Ben Letham

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#The author/copyright holder can be contacted at bletham@gmail.com
'''Handling of the timing window'''

import pygtk
pygtk.require('2.0')
import gtk
import fstimer.gui
import fstimer.gui.editt0
import fstimer.gui.edittime
import fstimer.gui.editblocktimes
import datetime
import time
import os
import re
import json

class MergeError(Exception):
    pass

class TimingWin(gtk.Window):
    '''Handling of the timing window'''

    def __init__(self, path, parent, timebtn, strpzeros, rawtimes, timing, print_cb):
        '''Builds and display the compilation error window'''
        super(TimingWin, self).__init__(gtk.WINDOW_TOPLEVEL)
        self.path = path
        self.timebtn = timebtn
        self.strpzeros = strpzeros
        self.rawtimes = rawtimes
        self.wineditblocktime = None
        self.winedittime = None
        self.t0win = None
        self.modify_bg(gtk.STATE_NORMAL, fstimer.gui.bgcolor)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title('fsTimer - ' + path)
        self.set_position(gtk.WIN_POS_CENTER)
        self.connect('delete_event', lambda b, jnk: self.done_timing(b))
        self.set_border_width(10)
        self.set_size_request(450, 450)
        # We will put the timing info in a liststore in a scrolledwindow
        self.timemodel = gtk.ListStore(str, str)
        # We will put the liststore in a treeview
        self.timeview = gtk.TreeView()
        column = gtk.TreeViewColumn('ID', gtk.CellRendererText(), text=0)
        self.timeview.append_column(column)
        column = gtk.TreeViewColumn('Time', gtk.CellRendererText(), text=1)
        self.timeview.append_column(column)
        self.timeview.set_model(self.timemodel)
        self.timeview.connect('size-allocate', self.scroll_times)
        treeselection = self.timeview.get_selection()
        # make it multiple selecting
        treeselection.set_mode(gtk.SELECTION_MULTIPLE)
        # And put it in a scrolled window, in an alignment
        self.timesw = gtk.ScrolledWindow()
        self.timesw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.timesw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.timesw.add(self.timeview)
        timealgn = gtk.Alignment(0, 0, 1, 1)
        timealgn.add(self.timesw)
        self.entrybox = gtk.Entry(max=40)
        self.offset = 0 #this is len(times) - len(ids)
        self.entrybox.connect('activate', self.record_time)
        self.entrybox.connect('changed', self.check_for_newtime)
        # And we will save our file
        self.timestr = re.sub(' +', '_', time.ctime()).replace(':', '')
        # Now lets go on to boxes
        tophbox = gtk.HBox()
        # our default t0, and the stuff on top for setting/edit t0
        self.t0 = 0.
        btn_t0 = gtk.Button('Start!')
        btn_t0.connect('clicked', self.set_t0)
        btn_editt0 = gtk.Button(stock=gtk.STOCK_EDIT)
        btn_editt0.connect('clicked', self.edit_t0)
        tophbox.pack_start(btn_t0, False, False, 8)
        tophbox.pack_start(btn_editt0, False, False, 8)
        self.t0_label = gtk.Label('t0: '+str(self.t0))
        tophbox.pack_start(self.t0_label, True, True, 8)
        timevbox1 = gtk.VBox(False, 8)
        timevbox1.pack_start(tophbox, False, False, 0)
        timevbox1.pack_start(timealgn, True, True, 0)
        timevbox1.pack_start(self.entrybox, False, False, 0)
        # we will keep track of how many racers are still out.
        self.racers_reg = timing.keys()
        self.racers_total = str(len(self.racers_reg))
        self.racers_in = 0
        self.racerslabel = gtk.Label()
        self.racerslabel.set_markup(str(self.racers_in)+' racers checked in out of '+self.racers_total+' registered.')
        timevbox1.pack_start(self.racerslabel, False, False, 0)
        vbox1align = gtk.Alignment(0, 0, 1, 1)
        vbox1align.add(timevbox1)
        # buttons on the right side
        btnDROPID = gtk.Button('Drop ID')
        btnDROPID.connect('clicked', self.timing_rm_ID)
        btnDROPTIME = gtk.Button('Drop time')
        btnDROPTIME.connect('clicked', self.timing_rm_time)
        btnEDIT = gtk.Button(stock=gtk.STOCK_EDIT)
        btnEDIT.connect('clicked', self.edit_time)
        btnPRINT = gtk.Button(stock=gtk.STOCK_PRINT)
        btnPRINT.connect('clicked', print_cb, False)
        btnSAVE = gtk.Button(stock=gtk.STOCK_SAVE)
        btnSAVE.connect('clicked', self.save_times)
        btnCSV = gtk.Button('Save CSV')
        btnCSV.connect('clicked', print_cb, True)
        btnRESUME = gtk.Button('Resume')
        btnRESUME.connect('clicked', self.resume_times, False)
        btnMERGE = gtk.Button('Merge')
        btnMERGE.connect('clicked', self.resume_times, True)
        btnOK = gtk.Button('Done')
        btnOK.connect('clicked', self.done_timing)
        vsubbox = gtk.VBox(False, 8)
        vsubbox.pack_start(btnDROPID, False, False, 0)
        vsubbox.pack_start(btnDROPTIME, False, False, 0)
        vsubbox.pack_start(btnEDIT, False, False, 40)
        vsubbox.pack_start(btnPRINT, False, False, 0)
        vsubbox.pack_start(btnSAVE, False, False, 0)
        vsubbox.pack_start(btnCSV, False, False, 0)
        vsubbox.pack_start(btnRESUME, False, False, 0)
        vsubbox.pack_start(btnMERGE, False, False, 0)
        vsubbox.pack_start(btnOK, False, False, 0)
        vspacer = gtk.Alignment(1, 1, 0, 0)
        vspacer.add(vsubbox)
        timehbox = gtk.HBox(False, 8)
        timehbox.pack_start(vbox1align, True, True, 0)
        timehbox.pack_start(vspacer, False, False, 0)
        self.add(timehbox)
        self.show_all()

    def check_for_newtime(self, jnk_unused):
        '''Handles entering of a new time'''
        if self.entrybox.get_text() == self.timebtn:
            self.new_blank_time()

    def scroll_times(self, jnk1_unused, jnk2_unused):
        '''handles scrolling of the time window'''
        adj = self.timesw.get_vadjustment()
        adj.set_value(0)

    def set_t0(self, jnk_unused):
        '''Handles click on Start button
           Sets t0 to the current time'''
        self.t0 = time.time()
        self.t0_label.set_markup('t0: ' + str(self.t0))

    def edit_t0(self, jnk_unused):
        '''Handles click on Edit button for the t0 value.
           Loads up a window and query the new t0'''
        self.t0win = fstimer.gui.editt0.EditT0Win(self.path, self, self.t0, self.ok_editt0)

    def ok_editt0(self, t0):
        '''Handles click on OK after t0 edition'''
        self.t0 = t0
        self.t0_label.set_markup('t0: '+str(self.t0))
        self.t0win.hide()

    def edit_time(self, jnk_unused):
        '''Handles click on Edit button for a time
           Chooses which edit time window to open,
           depending on how many items are selected'''
        treeselection = self.timeview.get_selection()
        pathlist = treeselection.get_selected_rows()[1]
        if len(pathlist) == 0:
            # we don't load any windows or do anything
            pass
        elif len(pathlist) == 1:
            # load the edit_single window
            treeiter = self.timemodel.get_iter(pathlist[0])
            old_id, old_time = self.timemodel.get(treeiter, 0, 1)
            self.winedittime = fstimer.gui.edittime.EditTimeWin \
                (self, old_id, old_time,
                 lambda id, time: self.editsingletimedone(treeiter, id, time))
        else:
            self.wineditblocktime = fstimer.gui.editblocktimes.EditBlockTimesWin \
                (self, lambda op, time: self.editblocktimedone(pathlist, op, time))
        return

    def editsingletimedone(self, treeiter, new_id, new_time):
        '''Handled result of the edition of a given time'''
        row = self.timemodel.get_path(treeiter)[0]
        if row < self.offset:
            if new_id:
                # we are putting an ID in a slot that we hadn't reached yet
                # Fill in any other missing ones up to this point with ''.
                ids = [str(new_id)]
                ids.extend(['' for i_unused in range(self.offset-row-1)])
                ids.extend(self.rawtimes['ids'])
                self.rawtimes['ids'] = list(ids)
                self.offset = row #the new offset
                self.rawtimes['times'][row] = str(new_time) #the new time
                self.timemodel.set_value(treeiter, 0, str(new_id))
                self.timemodel.set_value(treeiter, 1, str(new_time))
            elif new_time:
                # we are adjusting the time only.
                self.rawtimes['times'][row] = str(new_time) #the new time
                self.timemodel.set_value(treeiter, 1, str(new_time))
            else:
                # we are clearing this entry. pop it from time and adjust offset.
                self.rawtimes['times'].pop(row)
                self.offset -= 1
                self.timemodel.remove(treeiter)
        elif row == self.offset and new_time and not new_id:
            # then we are clearing the most recent ID.
            # We pop it and adjust self.offset and adjust the time.
            self.rawtimes['ids'].pop(0)
            self.rawtimes['times'][row] = str(new_time)
            self.offset += 1
            self.timemodel.set_value(treeiter, 0, str(new_id))
            self.timemodel.set_value(treeiter, 1, str(new_time))
        elif row < -self.offset:
            # Here we are making edits to a slot where there is an ID, but no time.
            if new_time:
                #we are putting a time in a slot that we hadn't reached yet. Fill in any other missing ones up to this point with blanks.
                times = [str(new_time)]
                times.extend(['' for i_unused in range(-self.offset-row-1)])
                times.extend(self.rawtimes['times'])
                self.rawtimes['times'] = list(times)
                self.offset = -row #the new offset
                self.rawtimes['ids'][row] = str(new_id) #the new time
                self.timemodel.set_value(treeiter, 0, str(new_id))
                self.timemodel.set_value(treeiter, 1, str(new_time))
            elif new_id:
                #we are adjusting the id only.
                self.rawtimes['ids'][row] = str(new_id) #the new time
                self.timemodel.set_value(treeiter, 0, str(new_id))
            else:
                #we are clearing this entry. pop it from id and adjust offset.
                self.rawtimes['ids'].pop(row)
                self.offset += 1
                self.timemodel.remove(treeiter)
        else:
            if not new_time and not new_id:
                # we are clearing the entry
                if self.offset > 0:
                    self.rawtimes['ids'].pop(row-self.offset)
                    self.rawtimes['times'].pop(row)
                elif self.offset <= 0:
                    self.rawtimes['ids'].pop(row)
                    self.rawtimes['times'].pop(row+self.offset)
                self.timemodel.remove(treeiter)
            else:
                # adjust the entry
                if self.offset > 0:
                    self.rawtimes['ids'][row-self.offset] = str(new_id)
                    self.rawtimes['times'][row] = str(new_time)
                elif self.offset <= 0:
                    self.rawtimes['ids'][row] = str(new_id)
                    self.rawtimes['times'][row+self.offset] = str(new_time)
                self.timemodel.set_value(treeiter, 0, str(new_id))
                self.timemodel.set_value(treeiter, 1, str(new_time))
        self.winedittime.hide()

    def editblocktimedone(self, pathlist, operation, timestr):
        '''Handled result of the edition of a block of times
           Goes through every time in pathlist and do the requested operation'''
        for path in pathlist:
            # Figure out which row this is, and which treeiter
            treeiter = self.timemodel.get_iter(path)
            row = path[0]
            # Now figure out the new time. First get the old time as a string
            old_time_str = self.timemodel.get_value(treeiter, 1)
            # Now we convert it to timedelta
            try:
                d = re.match(r'((?P<days>\d+) days, )?(?P<hours>\d+):'r'(?P<minutes>\d+):(?P<seconds>\d+)', str(old_time_str)).groupdict(0)
                old_time = datetime.timedelta(**dict(((key, int(value)) for key, value in d.items())))
                # Now the time adjustment
                adj_time_str = timestr #the input string
                dadj = re.match(r'((?P<days>\d+) days, )?(?P<hours>\d+):'r'(?P<minutes>\d+):(?P<seconds>\d+)', str(adj_time_str)).groupdict(0)
                adj_time = datetime.timedelta(**dict(((key, int(value)) for key, value in dadj.items())))
                # Combine the timedeltas to get the new time
                if operation == 'ADD':
                    new_time = str(old_time + adj_time)
                elif operation == 'SUBTRACT':
                    if old_time > adj_time:
                        new_time = str(old_time - adj_time)
                    else:
                        new_time = '0:00:00' #We don't allow negative times.
                # Save them, and write out to the timemodel
                self.rawtimes['times'][row] = str(new_time)
                self.timemodel.set_value(treeiter, 1, str(new_time))
            except AttributeError:
                # This will happen for instance if the path has a blank time
                pass
        self.wineditblocktime.hide()

    def timing_rm_ID(self, jnk_unused):
        '''Handles click on the Drop ID button
           Throws up an 'are you sure' dialog box, and drop if yes.'''
        treeselection = self.timeview.get_selection()
        pathlist = treeselection.get_selected_rows()[1]
        if len(pathlist) == 0:
            # we don't load any windows or do anything
            pass
        elif len(pathlist) > 1:
            # this is a one-at-a-time operation
            pass
        elif len(pathlist) == 1:
            # Figure out what row this is in the timeview
            row = pathlist[0][0]
            # Now figure out what index in self.rawtimes['ids'] it is.
            ididx = row-max(0, self.offset)
            if ididx >= 0:
                # Otherwise, there is no ID here so there is nothing to do.
                # Ask if we are sure.
                rmID_dialog = gtk.MessageDialog(self,
                                                gtk.DIALOG_MODAL,
                                                gtk.MESSAGE_QUESTION,
                                                gtk.BUTTONS_YES_NO,
                                                'Are you sure you want to drop this ID and shift all later IDs down earlier in the list?\nThis cannot be undone.')
                rmID_dialog.set_title('Woah!')
                rmID_dialog.set_default_response(gtk.RESPONSE_NO)
                response = rmID_dialog.run()
                rmID_dialog.destroy()
                if response == gtk.RESPONSE_YES:
                    # Make the shift in self.rawtimes and self.offset
                    self.rawtimes['ids'].pop(ididx)
                    self.offset += 1
                    # And now shift everything on the display.
                    rowcounter = int(row)
                    for i in range(ididx-1, -1, -1):
                        # Write rawtimes[i] into row rowcounter
                        treeiter = self.timemodel.get_iter((rowcounter,))
                        self.timemodel.set_value(treeiter, 0, str(self.rawtimes['ids'][i]))
                        rowcounter -= 1
                    # Now we tackle the last value - there are two possibilities.
                    if self.offset > 0:
                      # There is a buffer of times, and this one should be cleared.
                      treeiter = self.timemodel.get_iter((rowcounter,))
                      self.timemodel.set_value(treeiter, 0, '')
                    else:
                      # There is a blank row at the top which should be removed.
                      treeiter = self.timemodel.get_iter((rowcounter,))
                      self.timemodel.remove(treeiter)

    def timing_rm_time(self, jnk_unused):
        '''Handles click on Drop time comment
           Throws up an 'are you sure' dialog box, and drop if yes.'''
        treeselection = self.timeview.get_selection()
        pathlist = treeselection.get_selected_rows()[1]
        if len(pathlist) == 0:
            # we don't load any windows or do anything
            pass
        elif len(pathlist) > 1:
            # this is a one-at-a-time operation
            pass
        elif len(pathlist) == 1:
            # Figure out what row this is in the timeview
            row = pathlist[0][0]
            # Now figure out what index in self.rawtimes['times'] it is.
            timeidx = row-max(0, -self.offset)
            if timeidx >= 0:
                # Otherwise, there is no time here so there is nothing to do.
                # Ask if we are sure.
                rmtime_dialog = gtk.MessageDialog(self,
                                                  gtk.DIALOG_MODAL,
                                                  gtk.MESSAGE_QUESTION,
                                                  gtk.BUTTONS_YES_NO,
                                                  'Are you sure you want to drop this time and shift all later times down earlier in the list?\nThis cannot be undone.')
                rmtime_dialog.set_title('Woah!')
                rmtime_dialog.set_default_response(gtk.RESPONSE_NO)
                response = rmtime_dialog.run()
                rmtime_dialog.destroy()
                if response == gtk.RESPONSE_YES:
                    # Make the shift in self.rawtimes and self.offset
                    self.rawtimes['times'].pop(timeidx)
                    self.offset -= 1
                    # And now shift everything on the display.
                    rowcounter = int(row)
                    for i in range(timeidx-1, -1, -1):
                        # Write rawtimes[i] into row rowcounter
                        treeiter = self.timemodel.get_iter((rowcounter,))
                        self.timemodel.set_value(treeiter, 1, str(self.rawtimes['times'][i]))
                        rowcounter -= 1
                    # Now we tackle the last value - there are two possibilities.
                    if self.offset < 0:
                        # There is a buffer of IDs, and this one should be cleared.
                        treeiter = self.timemodel.get_iter((rowcounter,))
                        self.timemodel.set_value(treeiter, 1, '')
                    else:
                        # there is a blank row at the top which should be removed.
                        treeiter = self.timemodel.get_iter((rowcounter,))
                        self.timemodel.remove(treeiter)

    def resume_times(self, jnk_unused, isMerge):
        '''Handles click on Resume button'''
        chooser = gtk.FileChooserDialog(title='Choose timing results to resume', action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
        chooser.set_current_folder(os.sep.join([os.getcwd(), self.path]))
        ffilter = gtk.FileFilter()
        ffilter.set_name('Timing results')
        ffilter.add_pattern('*_times.json')
        chooser.add_filter(ffilter)
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
            try:
                with open(filename, 'rb') as fin:
                    saveresults = json.load(fin)
                newrawtimes = saveresults['rawtimes']
                if isMerge:
                    if self.rawtimes['ids'] or newrawtimes['times']:
                        # we only accept merge of pure times with pure ids
                        raise MergeError('Merge is only dealing with pure ids merged into pure times')
                    self.rawtimes['ids'] = newrawtimes['ids']
                else:
                    self.rawtimes = newrawtimes
                    self.timestr = saveresults['timestr']
                    self.t0 = saveresults['t0']
                    self.t0_label.set_markup('t0: '+str(self.t0))
                self.offset = len(self.rawtimes['times']) - len(self.rawtimes['ids'])
                # Compute how many racers have checked in
                for ID in self.rawtimes['ids']:
                    try:
                        self.racers_reg.remove(ID)
                        self.racers_in += 1
                    except ValueError:
                        pass
                # And add them to the display.
                self.racerslabel.set_markup(str(self.racers_in)+' racers checked in out of '+self.racers_total+' registered.')
                self.timemodel.clear()
                if self.offset >= 0:
                    adj_ids = ['' for i_unused in range(self.offset)]
                    adj_ids.extend(self.rawtimes['ids'])
                    adj_times = list(self.rawtimes['times'])
                elif self.offset < 0:
                    adj_times = ['' for i_unused in range(-self.offset)]
                    adj_times.extend(self.rawtimes['times'])
                    adj_ids = list(self.rawtimes['ids'])
                for entry in zip(adj_ids, adj_times):
                    self.timemodel.append(list(entry))
                chooser.destroy()
            except (IOError, ValueError, TypeError, MergeError), e:
                chooser.destroy()
                error_dialog = gtk.MessageDialog(self, gtk.DIALOG_MODAL,
                                                 gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                                 'ERROR: Failed to %s : %s.' % ('merge' if isMerge else 'result', e))
                error_dialog.set_title('Oops...')
                response = error_dialog.run()
                error_dialog.destroy()

    def save_times(self, jnk_unused):
        '''Handles click on the Save button
           jsonn dump to the already specified filename'''
        saveresults = {}
        saveresults['rawtimes'] = self.rawtimes
        saveresults['timestr'] = self.timestr
        saveresults['t0'] = self.t0
        with open(os.sep.join([self.path, self.path+'_'+self.timestr+'_times.json']), 'wb') as fout:
            json.dump(saveresults, fout)
        md = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Times saved!")
        md.run()
        md.destroy()

    def done_timing(self, source):
        '''Handles click on the Done button
           Gives two dialogs before closing.'''
        if str(type(source)) == "<type 'gtk.Button'>":
            oktime_dialog1 = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, 'Are you sure you want to leave?')
            oktime_dialog1.set_title('Really done?')
            response1 = oktime_dialog1.run()
            oktime_dialog1.destroy()
        else:
            # in case of delete_event the window closes regardless.
            response1 = gtk.RESPONSE_YES
        if response1 == gtk.RESPONSE_YES:
            oktime_dialog2 = gtk.MessageDialog(self, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, 'Do you want to save before finishing?\nUnsaved data will be lost.')
            oktime_dialog2.set_title('Save?')
            response2 = oktime_dialog2.run()
            oktime_dialog2.destroy()
            if response2 == gtk.RESPONSE_YES:
                self.save_times(None)
            self.hide()

    def record_time(self, jnk_unused):
        '''Handles a hit on enter in the entry box.
           An ID with times in the buffer gives the oldest (that is, fastest)
           time in the buffer to the ID
           An ID with no times in the buffer is added to a buffer of IDs
           An ID with the marktime symbol in it will first apply the ID
           and then mark the time.'''
        txt = self.entrybox.get_text()
        timemarks = txt.count(self.timebtn)
        txt = txt.replace(self.timebtn, '')
        if self.strpzeros:
            txt = txt.lstrip('0')
        # it is actually a result. (or a pass, which we treat as a result)
        # prepend to raw
        self.rawtimes['ids'].insert(0, txt)
        # add to the appropriate spot on timemodel.
        if self.offset > 0:
            # we have a time in the store to assign it to
             # put it in the last available time slot
            self.timemodel.set_value(self.timemodel.get_iter(self.offset-1), 0, txt)
        else:
            # It will just be added to the buffer of IDs by prepending to timemodel
            self.timemodel.prepend([txt, ''])
        self.offset -= 1
        for jnk_unused in range(timemarks):
            self.new_blank_time()
        # update the racer count.
        try:
            self.racers_reg.remove(txt)
            self.racers_in += 1
            self.racerslabel.set_markup(str(self.racers_in)+' racers checked in out of '+self.racers_total+' registered.')
        except ValueError:
            pass
        self.entrybox.set_text('')

    def new_blank_time(self):
        '''Record a new time'''
        t = str(datetime.timedelta(seconds=int(time.time()-self.t0)))
        self.rawtimes['times'].insert(0, t) #we prepend to rawtimes, just as we prepend to timemodel
        if self.offset >= 0:
            # No IDs in the buffer, so just prepend it to the liststore.
            self.timemodel.prepend(['', t])
        elif self.offset < 0:
            # IDs in the buffer, so add the time to the oldest ID
            # put it in the last available ID slot
            self.timemodel.set_value(self.timemodel.get_iter(-self.offset-1), 1, t)
        self.offset += 1
        self.entrybox.set_text('')