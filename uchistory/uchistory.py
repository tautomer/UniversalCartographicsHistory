import glob
import os
import json
import time

class UniversalCartographicsHistory:
    def __init__(self):
        self.log_path = os.path.expanduser('~') + \
            '\Saved Games\Frontier Developments\Elite Dangerous'
        self.verbose = 2
        self.history = {'cmdr': 0, 'count_fdfm': 0, 'count_fd': 0, 'count_fm': 0, 'cmdrs': {}}
        self.cmdr_id = ''
        self.cmdr = ''
        self.current_scan = {'count': 0, 'count_fdfm': 0, 'count_fd': 0, 'count_fm': 0}
        self.keys = ['fdfm', 'fd', 'fm']
        self.labels = ['First Discovery + Mapped', 'First Discovery', 'First Mapped']
        self.system_name = ''
        self.body_name = ''

    def check_ed_log_path(self):
        """check_ed_log_path [check if the path to ED log is correct]
        """
        if not os.path.isdir(self.log_path):
            raise ValueError(f'The path {self.log_path} does not exist!')
    
    def read_journals(self):
        self.check_ed_log_path()
        # find all ED logs
        journals = glob.glob(self.log_path + "\Journal.*.log")
        # sort by the last modified time in ascending order
        journals.sort(key=os.path.getmtime)
        if len(journals) == 0:
            raise ValueError(f'No ED log file found in {self.log_path}')
        # loop through all files
        for journal in journals:
            print(f'Reading {os.path.basename(journal)}')
            linenumber = 0
            with open(journal, 'r', encoding='UTF-8') as j: 
                line = j.readline() 
                while line:
                    line = j.readline() 
                    linenumber += 1
                    if linenumber % 100 == 0:
                        print(f'    Reading line no. {linenumber}')
                    self.read_event(line)
        self.write_output()

    def read_event(self, line):
        # find the current commander name and ID
        if line[38:57] == '"event":"Commander"':
            cmdr = json.loads(line)
            self.check_cmdr(cmdr)
        # find current system name
        elif line[38:55] == '"event":"FSDJump"':
            jump = json.loads(line)
            self.add_to_history(jump)
        # check FSS relate event
        # there are two types scans within this type
        # auto scan: sensor picks up body information automatically
        # detailed: maunally done in FSS UI
        # they do exactly the same thing
        elif line[38:52] == '"event":"Scan"':
            fss = json.loads(line)
            self.check_body(fss)
        # check DSS
        elif line[38:63] == '"event":"SAAScanComplete"':
            dss = json.loads(line)
            self.check_dss(dss)

    def check_cmdr(self, cmdr):
        self.cmdr = cmdr['Name']
        self.cmdr_id = cmdr['FID']
        # add cmdr to the history
        if self.cmdr_id not in self.history['cmdrs']:
            self.history['cmdr'] += 1
            self.history['cmdrs'][self.cmdr_id] = {'name': self.cmdr,
                                                   'count_fdfm': 0,
                                                   'count_fd': 0,
                                                   'count_fm': 0,
                                                   'discoveries': {}}

    def add_to_history(self, jump):
        if self.current_scan['count']:
            fdfm = self.current_scan['count_fdfm']
            fd = self.current_scan['count_fd']
            fm = self.current_scan['count_fm']
            self.update_counter(fdfm, fd, fm)
            history = self.history['cmdrs'][self.cmdr_id]['discoveries']
            if self.system_name not in history:
                history[self.system_name] = {}
                for i in self.keys:
                    if i in self.current_scan:
                        history[self.system_name][i] = self.current_scan[i]
            else:
                for i in self.keys:
                    if i in self.current_scan:
                        history[self.system_name][i].update(self.current_scan[i])
            self.current_scan = {'count': 0, 'count_fdfm': 0, 'count_fd': 0, 'count_fm': 0}
        self.system_name = jump['StarSystem']

    def check_body(self, fss):
        # add undiscovered bodies to fd
        bodyname = fss['BodyName']
        if not self.system_name:
            self.system_name = fss['StarSystem']
        # check unmapped bodies
        # well-known bodies are shown as undiscovered in game but already mapped
        # so this way will rule out the false positives for planets and moons
        # unless you are indeed the first one to map the bodies
        if not fss['WasMapped']:
            if not fss['WasDiscovered']:
                if 'fd' not in self.current_scan:
                    self.current_scan['fd'] = {bodyname: None}
                else:
                    self.current_scan['fd'][bodyname] = None
                self.current_scan['count'] += 1
                self.current_scan['count_fd'] += 1
            else:
                # belts and stars are not mapable
                # only planets and moons should be added to the unmapped set
                if 'Belt' not in bodyname and 'StarType' not in fss and not \
                    ('d' in self.current_scan and bodyname in self.current_scan['d']):
                    if 'unmapped' not in self.current_scan:
                        self.current_scan['unmapped'] = {bodyname: None}
                    else:
                        self.current_scan['unmapped'][bodyname] = None
                    if 'mapped' in self.current_scan and bodyname in self.current_scan['mapped']:
                        self.check_dss(fss)
        # sometimes for an already mapped planet
        # the FSS results will show up again after DSS and the status becomes unmapped
        # this part is used to fix this edge case
        else:
            # d for already discovered and mapped
            if 'd' not in self.current_scan:
                self.current_scan['d'] = {bodyname: None}
            else:
                self.current_scan['d'][bodyname] = None


    def check_dss(self, dss):
        bodyname = dss['BodyName']
        if not self.system_name:
            self.system_name = dss['StarSystem']
        # if this planet is undiscovered
        if 'fd' in self.current_scan and bodyname in self.current_scan['fd']:
            # remove from first discoery
            del self.current_scan['fd'][bodyname]
            self.current_scan['count_fd'] -= 1
            self.current_scan['count_fdfm'] += 1
            if 'fdfm' not in self.current_scan:
                self.current_scan['fdfm'] = {bodyname: None}
            else:
                self.current_scan['fdfm'][bodyname] = None
        # if this planet is discovered but not mapped
        elif 'unmapped' in self.current_scan and bodyname in self.current_scan['unmapped']:
            self.current_scan['count'] += 1
            self.current_scan['count_fm'] += 1
            if 'fm' not in self.current_scan:
                self.current_scan['fm'] = {bodyname: None}
            else:
                self.current_scan['fm'][bodyname] = None
        # sometimes the DSS results show in the log first followed by the FSS results
        # temporarily save the candidite to a dict called mapped
        else:
            if 'mapped' not in self.current_scan:
                self.current_scan['mapped'] = {bodyname: None}
            else:
                self.current_scan['mapped'][bodyname] = None

    def update_counter(self, fdfm, fd, fm):
        self.history['count_fdfm'] += fdfm
        self.history['count_fd'] += fd
        self.history['count_fm'] += fm
        self.history['cmdrs'][self.cmdr_id]['count_fdfm'] += fdfm
        self.history['cmdrs'][self.cmdr_id]['count_fd'] += fd
        self.history['cmdrs'][self.cmdr_id]['count_fm'] += fm

    def write_output(self):
        flnm = 'Universal Cartographics History Scan' + '.txt'
        with open(flnm, 'w') as summary:
            print(f'# Scan time {time.ctime()}', file=summary)
            print("""# Note: Well-known bodies are shown as undiscovered in game. While I can rule out\n\
# these false positives for planets, as they are already mapped but undiscovered.\n\
# I'm not able to do anything to the belts and stars as they are not mapable. As\n\
# a result, you'll see their names in the scan.\n""", file=summary)
            if len(self.history['cmdrs']) > 1:
                output = f"Number of CMDR's Found {self.history['cmdr']}\n"
                output += f"Total number of First Discovery + First Mapped: {self.history['count_fdfm']}\n"
                output += f"Total number of First Discovery: {self.history['count_fd']}\n"
                output += f"Total number of First Mapped: {self.history['count_fm']}\n"
                print(output, file=summary)
            for val in self.history['cmdrs'].values():
                if len(val) == 0:
                    continue
                cmdr = val['name']
                output = f'Commander Name: {cmdr}\n'
                output += f"Total number of First Discovery + First Mapped: {val['count_fdfm']}\n"
                output += f"Total number of First Discovery: {val['count_fd']}\n"
                output += f"Total number of First Mapped: {val['count_fm']}\n"
                print(output, file=summary)
                for system, discoveries in val['discoveries'].items():
                    output = f'System Name: {system}\n'
                    for idx, key in enumerate(self.keys):
                        if key in discoveries:                            
                            output += f'  {self.labels[idx]}:\n'
                            for body in discoveries[key].keys():
                                output += f'    {body}\n'
                    print(output, file=summary)

uc_history = UniversalCartographicsHistory()
uc_history.read_journals()