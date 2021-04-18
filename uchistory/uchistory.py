import glob
import os
import json
import time
import sys, getopt

class UniversalCartographicsHistory:
    def __init__(self):
        self.log_path = os.path.expanduser('~') + \
            '\Saved Games\Frontier Developments\Elite Dangerous'
        self.output = 'Universal Cartographics Histroy Scan.txt'
        self.verbose = 2
        self.history = {'cmdr': 0, 'count_fdfm': 0, 'count_fd': 0, 'count_fm': 0, 'cmdrs': {}}
        self.cmdr_id = ''
        self.cmdr = ''
        self.current_scan = {'count': 0, 'count_fdfm': 0, 'count_fd': 0, 'count_fm': 0}
        self.keys = ['fdfm', 'fd', 'fm']
        self.labels = ['First Discovery + Mapped', 'First Discovery', 'First Mapped']
        self.system_name = ''
        self.body_name = ''

    def check_ed_log_path(self, arg=''):
        """check_ed_log_path Check if the log path is a valid path

        Args:
            arg (str, optional): User-defined path. Defaults to ''.

        Raises:
            ValueError: if the path doesn't exist or is a file
        """
        if arg:
            if os.path.isdir(arg):
                uc_history.log_path = os.path.realpath(arg)
                return
            else:
                print(f'{arg} is not a valid path! Use default {self.log_path} instead') 
        if not os.path.isdir(self.log_path):
            raise ValueError(f'{self.log_path} is not a valid path!')

    def read_journals(self):
        """read_journals Loop through all journal files in the log_path folder

        Raises:
            ValueError: if there is no journal file in the folder
        """
        # find all ED logs
        journals = glob.glob(self.log_path + "/Journal.*.log")
        # sort by the last modified time in ascending order
        journals.sort(key=os.path.getmtime)
        # if there is no journal file found
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
        """read_event Read events related to UC discoveries in the journals

        Args:
            line (string): the line contain a single ED event
        """
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
        """check_cmdr check if the current CMDR name is already recorded

        [extended_summary]

        Args:
            cmdr (dict): json contains CMDR info
        """
        self.cmdr = cmdr['Name']
        self.cmdr_id = cmdr['FID']
        # add cmdr to the history
        if self.cmdr_id not in self.history['cmdrs']:
            self.history['cmdr'] += 1
            # you can delete the CMDR and re-create one with the same name
            # so the ID is used to distinguish between accounts
            self.history['cmdrs'][self.cmdr_id] = {'name': self.cmdr,
                                                   'count_fdfm': 0,
                                                   'count_fd': 0,
                                                   'count_fm': 0,
                                                   'discoveries': {}}

    def add_to_history(self, jump):
        """add_to_history Add the scan results of the previous system to the history if there is any new discovery 

        `FSDJump` event marks the arrival of the next system, so it's a good time
        to check the results in the previous one

        Args:
            jump (dict): json contains new system info
        """
        # if there are new findings
        if self.current_scan['count']:
            # update total counts
            fdfm = self.current_scan['count_fdfm']
            fd = self.current_scan['count_fd']
            fm = self.current_scan['count_fm']
            self.update_counter(fdfm, fd, fm)
            # add discovered bodies names to the history
            history = self.history['cmdrs'][self.cmdr_id]['discoveries']
            if self.system_name not in history:
                history[self.system_name] = {}
                for i in self.keys:
                    if i in self.current_scan:
                        history[self.system_name][i] = self.current_scan[i]
            # in case the system has been visited before and scanned again
            else:
                for i in self.keys:
                    if i in self.current_scan:
                        history[self.system_name][i].update(self.current_scan[i])
            # reset the dict for scans in the current system
            self.current_scan = {'count': 0, 'count_fdfm': 0, 'count_fd': 0, 'count_fm': 0}
        # update system name
        self.system_name = jump['StarSystem']

    def check_body(self, fss):
        """check_body Check body info for a FSS scan

        Args:
            fss (dict): json of a FSS scan entry
        """
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
        """check_dss Check if a DSS'd planets is unmapped or not

        Args:
            dss (dict): json of a DSS scan entry
        """
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
        """update_counter 
        
        Update the total counts of discoveries for first discovery and first
        mapped, first discovery only and first mapped only in the previous system

        Args:
            fdfm (int): first discovery and first mapped
            fd (int): first discovery
            fm (int): first mapped
        """
        self.history['count_fdfm'] += fdfm
        self.history['count_fd'] += fd
        self.history['count_fm'] += fm
        self.history['cmdrs'][self.cmdr_id]['count_fdfm'] += fdfm
        self.history['cmdrs'][self.cmdr_id]['count_fd'] += fd
        self.history['cmdrs'][self.cmdr_id]['count_fm'] += fm

    def write_output(self):
        """write_output Write summary to self.output file
        """
        with open(self.output, 'w') as summary:
            # print header
            text = (f'# Scan finished on {time.ctime()}\n'
                    '# Note: Well-known bodies are shown as undiscovered in game. While I can rule out\n'
                    '# these false positives for planets, as they are already mapped but undiscovered.\n'
                    "# I'm not able to do anything to the belts and stars as they are not mapable. As\n"
                    "# a result, you'll see their names in the scan.\n")
            print(text, file=summary)
            # if there are more than 1 CNDR found, print a summary of all CMDR's stats
            if len(self.history['cmdrs']) > 1:
                output = (f"Number of CMDR's Found {self.history['cmdr']}\n"
                          f"Total number of First Discovery + First Mapped: {self.history['count_fdfm']}\n"
                          f"Total number of First Discovery: {self.history['count_fd']}\n"
                          f"Total number of First Mapped: {self.history['count_fm']}\n")
                print(output, file=summary)
            # for each CMDR
            for val in self.history['cmdrs'].values():
                # if no discoery is made
                if len(val) == 0:
                    continue
                # summary for this CMDR
                output = (f"Commander Name: {val['name']}\n"
                          f"Total number of First Discovery + First Mapped: {val['count_fdfm']}\n"
                          f"Total number of First Discovery: {val['count_fd']}\n"
                          f"Total number of First Mapped: {val['count_fm']}\n")
                print(output, file=summary)
                # details on each system
                for system, discoveries in val['discoveries'].items():
                    # system summary
                    sys_summary = f'System Name: {system}\n'
                    for idx, key in enumerate(self.keys):
                        if key in discoveries:                            
                            label = self.labels[idx]
                            n = len(discoveries[key])
                            sys_summary += f'  {label}: {n} Bodies\n'
                            if self.verbose > 1:
                                # sort all body names in alphabet
                                bodies = sorted(list(discoveries[key]))
                                for body in bodies:
                                    sys_summary += f'    {body}\n'
                    print(sys_summary, file=summary)

def get_opt(args, history):
    """get_opt Get CLI options

    Args:
        args (list): list of CLI arguments
        history (UniversalCartographicsHistory): args should be passed here
    """
    def print_help(msg=''):
        """print_help print CLI help messages

        Args:
            msg (str, optional): Used when wrong options are passed. Defaults to ''.
        """
        text = ('Usage:\n'
                '  python.exe uchistory.py [OPTION...]\n\n'
                'Help Option:\n'
                '  -h, --help              Show this message\n\n'
                'E:D Log Path:\n'
                '  -l, --log-path=         Path to the E:D log files\n'
                '                          Defaults to C:\\Users\\username\\Saved Games\\Frontier Developments\\Elite Dangerous\n\n'
                'Output File:\n'
                '  -o, --output=           Output filename and path to save the scan results\n'
                '                          Defaults to Universal Cartographics Histroy Scan.txt in the current folder\n\n'
                'Output Level:\n'
                '  -v, --verbose=          Output verbose level\n'
                '                          Level 1 lists only the number of bodies discovered/mapped in the system\n'
                '                          Level 2 lists the body names as well\n'
                '                          Defaults to 2\n')
        print(text)
        sys.exit(msg)

    long_opts = ['help', 'log-path=', 'output=', 'vervbose=']
    try:
        opts, args = getopt.getopt(args, 'hl:o:v:', long_opts)
    except getopt.GetoptError:
        print_help('Wrong CLI options given. Check usage above.')
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print_help()
        elif opt in ("-l", "--log-path"):
            uc_history.check_ed_log_path(arg)
        elif opt in ("-o", "--output"):
            try:
                f = open(arg, 'w')
                f.close()
                history.output = arg
            except FileNotFoundError:
                print((f'Output {arg} provided contains wrong path. '
                       'Write to Universal Cartographics Histroy Scan.txt in the current folder.'))
            history.output = os.path.realpath(history.output)
        elif opt in ("-v", "--verbose"):
            try:
                arg = int(arg)
                if arg < 1 or arg > 2:
                    print(f"verbose={arg} isn't supported. Use default verbose=2")
                else:
                    history.verbose = arg
            except ValueError:                    
                print(f"{arg} isn't a valid integer number. Use default verbose=2")
    print('Log path is', history.log_path)
    print('Output file is', history.output)
    print('Verbose level is', history.verbose)

if __name__ == "__main__":
    uc_history = UniversalCartographicsHistory()
    get_opt(sys.argv[1:], uc_history)
    uc_history.read_journals()