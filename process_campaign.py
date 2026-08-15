#!/usr/bin/env python3
"""Turn a MekHQ campaign save into the markdown files this Jekyll site renders.

Works with modern MekHQ saves (0.50.x/0.51.x, where personnel live under
<humanResources> and forces are called <formations>) as well as the older
0.4x layout the script was originally written against.
"""

# ----------------------------------------------------------------------------
# Basic parameters - change as needed
# ----------------------------------------------------------------------------

# relative or absolute path to your mekhq directory including trailing /
# (relative paths are resolved against this script's directory)
mekhq_path = "../mekhq/MekHQ-0.51.00/"

# the name of your campaign file within the campaigns directory of your
# mekhq directory. Leave as '' to use the most recently modified save.
campaign_file = 'The Learning Ropes.cpnx.gz'

# change this to choose which personnel get loaded based on personnel roles
# in mekhq. Both modern and legacy role names are listed, so the same setting
# works no matter which version wrote the save.
# https://github.com/MegaMek/mekhq/blob/master/MekHQ/src/mekhq/campaign/personnel/enums/PersonnelRole.java
roles = ["MEKWARRIOR", "MECHWARRIOR", "LAM_PILOT",
         "VEHICLE_CREW_GROUND", "VEHICLE_CREW_NAVAL", "VEHICLE_CREW_VTOL",
         "GROUND_VEHICLE_DRIVER", "NAVAL_VEHICLE_DRIVER", "VTOL_PILOT",
         "VEHICLE_GUNNER", "VEHICLE_CREW",
         "AEROSPACE_PILOT", "CONVENTIONAL_AIRCRAFT_PILOT",
         "PROTOMEK_PILOT", "PROTOMECH_PILOT", "BATTLE_ARMOUR", "SOLDIER",
         "VESSEL_PILOT", "VESSEL_GUNNER", "VESSEL_CREW", "VESSEL_NAVIGATOR",
         "MEK_TECH", "MECH_TECH", "MECHANIC", "AERO_TEK", "AERO_TECH",
         "BA_TECH", "DOCTOR",
         "ADMINISTRATOR_COMMAND", "ADMINISTRATOR_LOGISTICS",
         "ADMINISTRATOR_TRANSPORT", "ADMINISTRATOR_HR"]

roles_dict = {
    "MEKWARRIOR": "Mechwarrior",
    "MECHWARRIOR": "Mechwarrior",
    "LAM_PILOT": "LAM Pilot",
    "VEHICLE_CREW_GROUND": "Vehicle Crew",
    "VEHICLE_CREW_NAVAL": "Naval Vessel Crew",
    "VEHICLE_CREW_VTOL": "VTOL Crew",
    "GROUND_VEHICLE_DRIVER": "Vehicle Driver",
    "NAVAL_VEHICLE_DRIVER": "Naval Vessel Driver",
    "VTOL_PILOT": "VTOL Pilot",
    "VEHICLE_GUNNER": "Vehicle Gunner",
    "VEHICLE_CREW": "Vehicle Crew",
    "AEROSPACE_PILOT": "Aerospace Pilot",
    "CONVENTIONAL_AIRCRAFT_PILOT": "Conventional Fighter Pilot",
    "PROTOMEK_PILOT": "Protomech Pilot",
    "PROTOMECH_PILOT": "Protomech Pilot",
    "BATTLE_ARMOUR": "Battle Armor Soldier",
    "SOLDIER": "Soldier",
    "VESSEL_PILOT": "Space Vessel Pilot",
    "VESSEL_GUNNER": "Space Vessel Gunner",
    "VESSEL_CREW": "Space Vessel Crew",
    "VESSEL_NAVIGATOR": "Hyperspace Navigator",
    "MEK_TECH": "Mech Tech",
    "MECH_TECH": "Mech Tech",
    "MECHANIC": "Mechanic",
    "AERO_TEK": "Aero Tech",
    "AERO_TECH": "Aero Tech",
    "BA_TECH": "Battle Armor Tech",
    "ASTECH": "Astech",
    "DOCTOR": "Doctor",
    "MEDIC": "Medic",
    "ADMINISTRATOR_COMMAND": "Admin/Command",
    "ADMINISTRATOR_LOGISTICS": "Admin/Logistical",
    "ADMINISTRATOR_TRANSPORT": "Admin/Transport",
    "ADMINISTRATOR_HR": "Admin/HR",
    "DEPENDENT": "Dependent",
    "NONE": "None"
}

# mission, scenario, and personnel status names
mission_status_dict = {
    "ACTIVE": "Active",
    "SUCCESS": "Success",
    "PARTIAL": "Partial Success",
    "FAILED": "Failed",
    "BREACH": "Breached",
    "BREACHED": "Breached"
}
scenario_status_dict = {
    "CURRENT": "Current",
    "DECISIVE_VICTORY": "Decisive Victory",
    "VICTORY": "Victory",
    "MARGINAL_VICTORY": "Marginal Victory",
    "PYRRHIC_VICTORY": "Pyrrhic Victory",
    "DRAW": "Draw",
    "MARGINAL_DEFEAT": "Marginal Defeat",
    "DEFEAT": "Defeat",
    "DECISIVE_DEFEAT": "Decisive Defeat",
    "FLEET_IN_BEING": "Fleet in Being",
    "REFUSED_ENGAGEMENT": "Refused Engagement"
}
# the numeric statuses very old saves used, in enum order
personnel_status_names = ['Active', 'Retired', 'Killed in Action',
                          'Missing in Action']
# anything not listed here is title-cased automatically (KIA -> "Killed in
# Action" style entries are the ones worth spelling out)
personnel_status_dict = {
    "ACTIVE": "Active",
    "KIA": "Killed in Action",
    "MIA": "Missing in Action",
    "POW": "Prisoner of War",
    "AWOL": "AWOL",
    "ON_LEAVE": "On Leave",
    "ON_MATERNITY_LEAVE": "On Maternity Leave",
    "STUDENT": "Student",
    "MISSING": "Missing",
    "RETIRED": "Retired",
    "RESIGNED": "Resigned",
    "SACKED": "Sacked",
    "LEFT": "Left",
    "DESERTED": "Deserted",
    "DEFECTED": "Defected",
    "HOMICIDE": "Killed",
    "WOUNDS": "Died of Wounds",
    "DISEASE": "Died of Disease",
    "CONTAGIOUS_DISEASE": "Died of Disease",
    "ACCIDENTAL": "Killed in Accident",
    "NATURAL_CAUSES": "Died of Natural Causes",
    "OLD_AGE": "Died of Old Age",
    "MEDICAL_COMPLICATIONS": "Died of Medical Complications",
    "PREGNANCY_COMPLICATIONS": "Died in Childbirth",
    "UNDETERMINED": "Died of Undetermined Causes",
    "SUICIDE": "Died by Suicide",
    "ENEMY_BONDSMAN": "Enemy Bondsman",
    "BONDSREF": "Bondsref",
    "SEPPUKU": "Seppuku",
    "BACKGROUND_CHARACTER": "Background Character",
    "IMPRISONED": "Imprisoned",
    "DISHONORABLY_DISCHARGED": "Dishonorably Discharged",
    "CAMP_FOLLOWER": "Camp Follower"
}

# skill level names. Modern MekHQ adds Heroic and Legendary above Elite.
skill_level_names = ["Ultra-Green", "Green", "Regular", "Veteran", "Elite",
                     "Heroic", "Legendary"]

# which skills describe each role, best first. The first name found on a
# person wins, so old and new skill names can both be listed.
role_skills = {
    "MEKWARRIOR": (["Gunnery/Mek", "Gunnery/Mech"],
                   ["Piloting/Mek", "Piloting/Mech"]),
    "LAM_PILOT": (["Gunnery/Mek", "Gunnery/Mech"],
                  ["Piloting/Mek", "Piloting/Mech"]),
    "AEROSPACE_PILOT": (["Gunnery/Aerospace"], ["Piloting/Aerospace"]),
    "CONVENTIONAL_AIRCRAFT_PILOT": (["Gunnery/Aircraft"],
                                    ["Piloting/Aircraft", "Piloting/Jet"]),
    "VEHICLE_CREW_GROUND": (["Piloting/Ground Vehicle"], ["Gunnery/Vehicle"]),
    "VEHICLE_CREW_NAVAL": (["Piloting/Naval"], ["Gunnery/Vehicle"]),
    "VEHICLE_CREW_VTOL": (["Piloting/VTOL"], ["Gunnery/Vehicle"]),
    "GROUND_VEHICLE_DRIVER": (["Piloting/Ground Vehicle"], []),
    "NAVAL_VEHICLE_DRIVER": (["Piloting/Naval"], []),
    "VTOL_PILOT": (["Piloting/VTOL"], []),
    "VEHICLE_GUNNER": (["Gunnery/Vehicle"], []),
    "VEHICLE_CREW": (["Tech/Mechanic"], []),
    "PROTOMEK_PILOT": (["Gunnery/ProtoMek", "Gunnery/Protomech"], []),
    "PROTOMECH_PILOT": (["Gunnery/ProtoMek", "Gunnery/Protomech"], []),
    "BATTLE_ARMOUR": (["Gunnery/BattleArmor", "Gunnery/Battlesuit"],
                      ["Anti-Mek (Climbing)", "Anti-Mek", "Anti-Mech"]),
    "SOLDIER": (["Small Arms"], []),
    "VESSEL_PILOT": (["Piloting/Spacecraft"], []),
    "VESSEL_GUNNER": (["Gunnery/Spacecraft"], []),
    "VESSEL_CREW": (["Tech/Vessel"], []),
    "VESSEL_NAVIGATOR": (["Navigation/Any", "Hyperspace Navigation"], []),
    "MEK_TECH": (["Tech/Mek", "Tech/Mech"], []),
    "MECH_TECH": (["Tech/Mek", "Tech/Mech"], []),
    "MECHANIC": (["Tech/Mechanic"], []),
    "AERO_TEK": (["Tech/Aero"], []),
    "AERO_TECH": (["Tech/Aero"], []),
    "BA_TECH": (["Tech/BattleArmor", "Tech/BA"], []),
    "ASTECH": (["Astech"], []),
    "DOCTOR": (["Surgery/Any", "Doctor"], []),
    "MEDIC": (["MedTech/Any", "Medtech"], []),
    "ADMINISTRATOR_COMMAND": (["Administration"], []),
    "ADMINISTRATOR_LOGISTICS": (["Administration"], []),
    "ADMINISTRATOR_TRANSPORT": (["Administration"], []),
    "ADMINISTRATOR_HR": (["Administration"], [])
}

# beginning of portait paths, only change if default image changes
portrait_paths = {
    "default.gif": "default.gif"
}

# skill type dictionary
skill_dict = {
}

# ----------------------------------------------------------------------------
# imports
# ----------------------------------------------------------------------------

import xml.etree.ElementTree as ET
import re
import datetime
from dateutil import relativedelta
from html import unescape
import os
import sys
import glob
from shutil import copyfile
import gzip

# everything this script reads and writes is relative to its own directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# the settings above can also be given on the command line:
#   ./process_campaign.py "My Campaign.cpnx.gz" ../mekhq-0.51.00/
if(len(sys.argv) > 1):
    campaign_file = sys.argv[1]
if(len(sys.argv) > 2):
    mekhq_path = sys.argv[2]

if not mekhq_path.endswith(('/', '\\')):
    mekhq_path = mekhq_path + '/'

# ----------------------------------------------------------------------------
# custom functions
# ----------------------------------------------------------------------------

# clean out punctuation and replace spaces with - for url links and slugs
def urlify(s):
    # strip leading and trailing whitespace
    s = s.strip()
    # Remove all non-word characters (everything except numbers and letters)
    s = re.sub(r"[^\w\s]", '', s)
    # Replace all runs of whitespace with a single dash
    s = re.sub(r"\s+", '-', s)
    # slugs have trouble with numbers as the first letter, so add
    # a letter if this is the case
    if(s == ''):
        return 'unnamed'
    if(s[0].isdigit()):
        s = "n" + s
    return s.lower()

# quote a value so that odd characters (colons, quotes, #) can't break the
# YAML front matter
def yamlify(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'

# takes an xml element and returns either the text of element if it exists
# or an empty string otherwise
def get_xml_text(ele):
    if(ele is not None and ele.text is not None):
        return ele.text.strip()
    else:
        return ''

# find the first of several possible paths that exists, so that saves from
# different mekhq versions can be read with the same code
def find_first(ele, *paths):
    for path in paths:
        found = ele.find(path)
        if(found is not None):
            return found
    return None

def find_first_text(ele, *paths):
    return get_xml_text(find_first(ele, *paths))

# take an xml element with a date in it and convert to date object
def get_xml_date(ele):
    if(ele is not None and ele.text is not None):
        date = ele.text.strip().split(" ")[0]
        try:
            return datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return None
    else:
        return None

# read portrait pathway. Need to check for special cases
def get_portrait_path(ele):
    path = get_xml_text(ele)
    if(path == '-- General --'):
        return ''
    else:
        return path

# read portrait file. Need to check for special cases
def get_portrait_file(ele):
    file_name = get_xml_text(ele)
    if(file_name == 'None'):
        return ''
    else:
        return file_name

def replace_portrait_name(portrait_file, slug):
    suffix = portrait_file.split('.')[-1]
    return slug + '.' + suffix

# turn an enum name we don't have a nicer label for into something readable
def prettify_enum(name):
    return name.replace('_', ' ').title()

# they switched over from int to enum for status
# so need to consider both ways
def get_person_status(status):
    if(status.isdigit()):
        index = int(status)
        if(index < len(personnel_status_names)):
            return personnel_status_names[index]
        return 'Active'
    return personnel_status_dict.get(status, prettify_enum(status))

def get_person_role(role):
    return roles_dict.get(role, prettify_enum(role))

# loop through kills and count ones belonging to this uuid
def count_kills(uuid, kills):
    nkills = 0
    if(kills is None):
        return 0
    for kill in kills.findall('kill'):
        kill_id = find_first(kill, 'pilotId', 'personId')
        if(kill_id is not None and kill_id.text is not None):
            if(uuid == kill_id.text.strip()):
                nkills = nkills + 1
    return nkills

# get the name of the unit assigned to person uuid
def get_unit_name(uuid, units):
    unit = units_by_id.get(uuid)
    if(unit is None):
        return None
    entity = unit.find('entity')
    if(entity is None):
        return ''
    return (entity.attrib.get('chassis', '') + ' ' +
            entity.attrib.get('model', '')).strip()

# loop through units and find the one assigned to a person by uuid
def find_unit(person, uuid, units):
    # modern saves record the assignment on the person
    unit_id = find_first_text(person, 'unitId', 'unitID')
    if(unit_id != '' and unit_id in units_by_id):
        return unit_id
    for unit in units.findall('unit'):
        for tag in ('driverId', 'pilotId', 'gunnerId', 'vesselCrewId'):
            for current_id in unit.findall(tag):
                if(current_id is not None and current_id.text is not None
                        and current_id.text.strip() == uuid):
                    return unit.attrib['id']
    return None

# forces are called formations in modern saves; both use the same shape
def get_subforces(force_ele):
    return find_first(force_ele, 'subforces', 'subForces', 'subFormations')

def get_force_children(forces_ele):
    return forces_ele.findall('force') + forces_ele.findall('formation')

# loop through all the forces identified in element list and output them to
# markdown files. At the end it calls itself to iteratively process the tree
def process_forces(forces_ele, parent_name, parent_slug):
    for force in get_force_children(forces_ele):
        short_force_name = find_first_text(force, 'name')
        if(parent_name is not None):
            if(parent_name == ''):
                full_force_name = short_force_name
            else:
                full_force_name = parent_name + ', ' + short_force_name
            slug = urlify(full_force_name)
        else:
            # top level force so special things
            full_force_name = ''
            slug = urlify(short_force_name)
        force_desc = find_first_text(force, 'desc', 'description')
        f = open('campaign/_forces/' + slug + '.md', 'w', encoding='utf-8')
        f.write('---\n')
        f.write('layout: force\n')
        f.write('title: ' + yamlify(short_force_name) + '\n')
        f.write('order: ' + force.attrib.get('id', '0') + '\n')
        f.write('slug: ' + slug + '\n')
        if(parent_name is not None):
            f.write('parent-name: ' + yamlify(parent_name) + '\n')
            f.write('parent-slug: ' + parent_slug + '\n')
        f.write('---\n\n')
        f.write(unescape(force_desc))
        f.close()
        subforces = get_subforces(force)
        if(subforces is not None):
            process_forces(subforces, full_force_name, slug)

# build a map of unit uuid -> full force name so personnel can be placed in
# the TO&E. Modern saves also store a formationId on each unit, which is used
# as a fallback for units the force tree doesn't list directly.
def map_forces(forces_ele, parent_name, unit_forces, force_names):
    for force in get_force_children(forces_ele):
        short_force_name = find_first_text(force, 'name')
        if(parent_name is None):
            full_force_name = ''
        elif(parent_name == ''):
            full_force_name = short_force_name
        else:
            full_force_name = parent_name + ', ' + short_force_name
        force_names[force.attrib.get('id', '')] = full_force_name
        units_ele = force.find('units')
        if(units_ele is not None):
            for unit in units_ele.findall('unit'):
                unit_id = unit.attrib.get('id', get_xml_text(unit))
                if(unit_id):
                    unit_forces[unit_id] = full_force_name
        subforces = get_subforces(force)
        if(subforces is not None):
            map_forces(subforces, full_force_name, unit_forces, force_names)

def find_force(unit_id):
    if(unit_id in unit_forces):
        return unit_forces[unit_id]
    unit = units_by_id.get(unit_id)
    if(unit is not None):
        formation_id = find_first_text(unit, 'formationId', 'forceId')
        if(formation_id in force_names):
            return force_names[formation_id]
    return None

# professions are the columns of a rankNames entry. Older rank files stop
# after TECH; modern ones add medical, admin, and civilian columns.
professions = ["MW", "ASF", "VEE", "NAVAL", "INF", "TECH", "MEDICAL",
               "ADMIN", "CIVILIAN"]
profession_alternates = {
    "--MW": 0, "--ASF": 1, "--AERO": 1, "--VEE": 2, "--NAVAL": 3,
    "--INF": 4, "--TECH": 5, "--MEDICAL": 6, "--MED": 6, "--ADMIN": 7,
    "--CIVILIAN": 8, "--CIV": 8
}
# which column a role reads its rank name from
role_professions = {
    "AEROSPACE_PILOT": 1, "CONVENTIONAL_AIRCRAFT_PILOT": 1,
    "VEHICLE_CREW_GROUND": 2, "VEHICLE_CREW_VTOL": 2,
    "GROUND_VEHICLE_DRIVER": 2, "VTOL_PILOT": 2, "VEHICLE_GUNNER": 2,
    "VEHICLE_CREW": 2,
    "VEHICLE_CREW_NAVAL": 3, "NAVAL_VEHICLE_DRIVER": 3,
    "VESSEL_PILOT": 3, "VESSEL_CREW": 3, "VESSEL_GUNNER": 3,
    "VESSEL_NAVIGATOR": 3,
    "BATTLE_ARMOUR": 4, "SOLDIER": 4,
    "MEK_TECH": 5, "MECH_TECH": 5, "MECHANIC": 5, "AERO_TEK": 5,
    "AERO_TECH": 5, "BA_TECH": 5, "ASTECH": 5,
    "DOCTOR": 6, "MEDIC": 6,
    "ADMINISTRATOR_COMMAND": 7, "ADMINISTRATOR_LOGISTICS": 7,
    "ADMINISTRATOR_TRANSPORT": 7, "ADMINISTRATOR_HR": 7
}

def find_rank(rank_level, rank_system, role):
    rank_list = all_rank_lists.get(rank_system)
    if(rank_list is None):
        rank_list = all_rank_lists.get(rank_system_default)
    if(rank_list is None):
        return None
    column = role_professions.get(role, 0)
    if(column >= len(rank_list)):
        column = 0
    if(rank_level < 0 or rank_level >= len(rank_list[0])):
        return None
    column = resolve_column(column, rank_level, rank_list)
    rank = get_rank_name(column, rank_level, rank_list)
    if(rank in ('-', '', 'None')):
        return None
    return rank

def get_rank_name(column, rank_level, rank_list):
    if(rank_level >= len(rank_list[column])):
        return ''
    return rank_list[column][rank_level]

# an empty column redirects to the profession named in its first rank, which
# is how mekhq lets e.g. techs share the mechwarrior rank names
def alternate_column(column, rank_list):
    if(column == 0 or len(rank_list[column]) == 0):
        return 0
    return profession_alternates.get(rank_list[column][0], 0)

# a column is "empty" when its first entry points elsewhere and it holds no
# rank names of its own
def is_empty_column(column, rank_list):
    if(column == 0 or len(rank_list[column]) == 0):
        return False
    if(rank_list[column][0] not in profession_alternates):
        return False
    return all(name in ('', '-') for name in rank_list[column][1:])

# work out which column a rank name actually comes from, following both
# whole-column redirects and the --XXX markers on individual ranks
def resolve_column(column, rank_level, rank_list):
    for _ in range(len(professions)):
        if(not is_empty_column(column, rank_list)):
            break
        new_column = alternate_column(column, rank_list)
        if(new_column == column):
            break
        column = new_column
    for _ in range(len(professions)):
        name = get_rank_name(column, rank_level, rank_list)
        if(name in ('', '-')):
            new_column = alternate_column(column, rank_list)
        elif(name in profession_alternates):
            new_column = profession_alternates[name]
        else:
            break
        if(new_column == column or new_column >= len(rank_list)):
            break
        column = new_column
    return column

# read one rank system into a list of columns (one per profession)
def process_rank_system(rsystem):
    columns = [[] for _ in professions]
    for rank in rsystem.findall("rank"):
        rank_names = get_xml_text(find_first(rank, 'rankNames', 'rankName'))
        names = rank_names.split(",")
        for i in range(len(columns)):
            columns[i].append(names[i] if i < len(names) else '-')
    return columns

def load_rank_file(path):
    if(not os.path.exists(path)):
        return
    try:
        rank_systems = ET.parse(path).getroot()
    except ET.ParseError as err:
        print('Warning: could not read ' + path + ': ' + str(err))
        return
    for rank_system in rank_systems.findall('rankSystem'):
        code = get_xml_text(rank_system.find('code'))
        if(code != '' and rank_system.find('rank') is not None):
            all_rank_lists[code] = process_rank_system(rank_system)

# read the rank system code off an element that either holds it as text or
# wraps it in a <code> child
def get_rank_system_code(ele):
    if(ele is None):
        return ''
    code = get_xml_text(ele.find('code'))
    if(code != ''):
        return code
    return get_xml_text(ele)

# custom class for skill type
class SkillType:
    def __init__(self, name, target, count_up, levels):
        self.name = name
        self.target = target
        self.count_up = count_up
        # ascending list of the level thresholds above ultra-green
        self.levels = levels

    def get_target_desc(self, skill):
        if(self.count_up):
            value = self.target + skill.level + skill.bonus
            return '+' + str(value)
        else:
            value = self.target - (skill.level + skill.bonus)
            return str(value) + '+'

    def get_skill_level(self, level):
        rating = 0
        for index, threshold in enumerate(self.levels):
            if(level >= threshold):
                rating = index + 1
        return min(rating, len(skill_level_names) - 1)

class Skill:
    def __init__(self, name, level, bonus):
        self.name = name
        self.level = level
        self.bonus = bonus

def get_skill_desc(sk1, sk2):
    if(sk1 is None or sk1.name not in skill_dict):
        return None
    lvl = skill_dict[sk1.name].get_skill_level(sk1.level)
    tgt_desc = skill_dict[sk1.name].get_target_desc(sk1)
    if(sk2 is not None and sk2.name in skill_dict):
        lvl2 = skill_dict[sk2.name].get_skill_level(sk2.level)
        lvl = int((lvl + lvl2) / 2)
        tgt_desc = tgt_desc + "/" + skill_dict[sk2.name].get_target_desc(sk2)
        tgt_desc = re.sub(r"\+", '', tgt_desc)
    return [skill_level_names[lvl], tgt_desc]

def pick_skill(skills, names):
    for name in names:
        if(name in skills):
            return skills[name]
    return None

def get_skill_report(person):
    role = find_first_text(person, 'primaryRole')
    skills = {}
    for skill in person.findall('skill'):
        sk_name = find_first_text(skill, 'type', 'name')
        try:
            sk_lvl = int(find_first_text(skill, 'level'))
            sk_bns = int(find_first_text(skill, 'bonus'))
        except ValueError:
            continue
        skills[sk_name] = Skill(sk_name, sk_lvl, sk_bns)
    primary_names, secondary_names = role_skills.get(role, ([], []))
    return get_skill_desc(pick_skill(skills, primary_names),
                          pick_skill(skills, secondary_names))

# ----------------------------------------------------------------------------
# Remove old files to start fresh
# ----------------------------------------------------------------------------

for directory in ['campaign/_forces', 'campaign/_missions',
                  'campaign/_personnel', 'campaign/_scenarios',
                  'assets/images/portraits']:
    os.makedirs(directory, exist_ok=True)
    for f in glob.glob(directory + '/*'):
        os.remove(f)

# ----------------------------------------------------------------------------
# Load the file and top-level information
# ----------------------------------------------------------------------------

campaign_dir = mekhq_path + 'campaigns/'
if(campaign_file == ''):
    saves = (glob.glob(campaign_dir + '*.cpnx') +
             glob.glob(campaign_dir + '*.cpnx.gz'))
    if(len(saves) == 0):
        sys.exit('No campaign saves found in ' + campaign_dir)
    campaign_file = os.path.basename(max(saves, key=os.path.getmtime))

campaign_save = campaign_dir + campaign_file
if(not os.path.exists(campaign_save)):
    sys.exit('Could not find campaign file ' + campaign_save)
print('Reading ' + campaign_save)

if campaign_file.endswith("gz"):
    gzipper = gzip.GzipFile(campaign_save)
    data = gzipper.read()
    campaign = ET.fromstring(data)
else:
    tree = ET.parse(campaign_save)
    campaign = tree.getroot()

print('MekHQ save version ' + campaign.attrib.get('version', 'unknown'))

# stuff we need
campaign_info = campaign.find('info')
date = get_xml_date(find_first(campaign_info, 'calendar', 'currentDate'))
kills = campaign.find('kills')
skill_types = campaign.find('skillTypes')
# personnel moved under humanResources in 0.50+, forces became formations
personnel = find_first(campaign, 'personnel', 'humanResources/personnel')
missions = campaign.find('missions')
forces = find_first(campaign, 'forces', 'formations')
units = campaign.find('units')

if(personnel is None or forces is None or units is None):
    sys.exit('This save does not look like a MekHQ campaign file.')

units_by_id = {}
for unit in units.findall('unit'):
    units_by_id[unit.attrib.get('id', '')] = unit

unit_forces = {}
force_names = {}
map_forces(forces, None, unit_forces, force_names)

# ----------------------------------------------------------------------------
# Process default and custom rank structure and skill types for later use
# ----------------------------------------------------------------------------

all_rank_lists = {}
load_rank_file(mekhq_path + 'data/universe/ranks.xml')
load_rank_file(mekhq_path + 'userdata/data/universe/ranks.xml')

# any rank system stored inside the campaign itself (custom systems) wins
for rank_system in campaign.iter('rankSystem'):
    if(rank_system.find('rank') is not None):
        code = get_xml_text(rank_system.find('code'))
        all_rank_lists[code if code != '' else 'CUSTOM'] = \
            process_rank_system(rank_system)

rank_system_default = get_rank_system_code(campaign_info.find('rankSystem'))
if(rank_system_default == '' or rank_system_default not in all_rank_lists):
    if('CUSTOM' in all_rank_lists):
        rank_system_default = 'CUSTOM'
    elif(len(all_rank_lists) > 0):
        rank_system_default = sorted(all_rank_lists)[0]
    else:
        rank_system_default = ''
        print('Warning: no rank systems found, ranks will be skipped.')

# process skill types
for skill_type in skill_types.findall("skillType"):
    skill_name = find_first_text(skill_type, 'name')
    try:
        skill_target = int(find_first_text(skill_type, 'target'))
    except ValueError:
        continue
    skill_count_up = find_first_text(skill_type, 'isCountUp',
                                     'countUp') == 'true'
    thresholds = []
    for level_tag in ['greenLvl', 'regLvl', 'vetLvl', 'eliteLvl',
                      'heroicLvl', 'legendaryLvl']:
        value = find_first_text(skill_type, level_tag)
        if(value != ''):
            thresholds.append(int(value))
    skill_dict[skill_name] = SkillType(skill_name, skill_target,
                                       skill_count_up, thresholds)

# ----------------------------------------------------------------------------
# Process the xml and output results to campaign directory
# ----------------------------------------------------------------------------

# process forces
process_forces(forces, None, None)

people_written = 0

# loop through personnel and print out markdown file for each one
for person in personnel.findall('person'):
    uuid = find_first_text(person, 'id')
    primary_role = find_first_text(person, 'primaryRole')
    if(primary_role not in roles):
        continue
    role_name = get_person_role(primary_role)
    first = find_first_text(person, 'givenName')
    surname = find_first_text(person, 'surname')
    bloodname = find_first_text(person, 'bloodname')
    name = find_first_text(person, 'name')
    if(name == ''):
        name = first
        if(surname != ''):
            name = name + ' ' + surname
    if(bloodname != '' and surname == ''):
        name = name + ' ' + bloodname
    name = name.strip()
    if(name == ''):
        continue
    status = get_person_status(find_first_text(person, 'status'))
    birthdate = get_xml_date(find_first(person, 'birthday', 'birthdate'))
    deathdate = get_xml_date(find_first(person, 'deathday', 'dateOfDeath'))
    clan = find_first_text(person, 'clanPersonnel', 'clan') == 'true'
    phenotype = find_first_text(person, 'phenotype')
    if(clan):
        if(phenotype in ('0', '', 'NONE')):
            phenotype = 'Freeborn Clan'
        else:
            phenotype = 'Trueborn Clan'
    else:
        phenotype = ''
    rank_number = find_first_text(person, 'rank')
    rank_name = None
    person_rank_system = get_rank_system_code(person.find('rankSystem'))
    if(person_rank_system == '' or person_rank_system == '-1'):
        person_rank_system = rank_system_default
    if(rank_number != ''):
        rank_name = find_rank(int(rank_number), person_rank_system,
                              primary_role)
    unit_id = find_unit(person, uuid, units)
    unit_name = None
    force_name = None
    if(unit_id is not None):
        unit_name = get_unit_name(unit_id, units)
        force_name = find_force(unit_id)
    if(birthdate is None):
        age = None
    elif(deathdate is not None):
        age = relativedelta.relativedelta(deathdate, birthdate).years
    else:
        age = relativedelta.relativedelta(date, birthdate).years
    title = name
    if(rank_name is not None):
        title = rank_name + ' ' + name
    bio = find_first_text(person, 'biography')
    skill_desc = get_skill_report(person)
    kill_count = count_kills(uuid, kills)
    portrait = person.find('portrait')
    if(portrait is None):
        portrait_file = ''
        portrait_path = ''
    else:
        portrait_file = get_portrait_file(portrait.find('filename'))
        portrait_path = get_portrait_path(portrait.find('category')) + \
            portrait_file
    callsign = find_first_text(person, 'callsign')
    f = open('campaign/_personnel/' + urlify(name) + '.md', 'w',
             encoding='utf-8')
    f.write('---\n')
    f.write('layout: bio\n')
    f.write('title: ' + yamlify(title) + '\n')
    f.write('name: ' + yamlify(name) + '\n')
    f.write('status: ' + yamlify(status) + '\n')
    if(phenotype != ''):
        f.write('phenotype: ' + yamlify(phenotype) + '\n')
    f.write('role: ' + primary_role + '\n')
    f.write('role-name: ' + yamlify(role_name) + '\n')
    if(skill_desc is not None):
        f.write('skill-level: ' + yamlify(skill_desc[0]) + '\n')
        f.write('skill-detail: ' + yamlify(skill_desc[1]) + '\n')
    if(callsign != ''):
        f.write('callsign: ' + yamlify(callsign) + '\n')
    if(kill_count > 0):
        f.write('kills: ' + str(kill_count) + '\n')
    if(age is not None):
        f.write('age: ' + str(age) + '\n')
    if(rank_number != ''):
        f.write('rank-number: ' + rank_number + '\n')
    if(rank_name is not None):
        f.write('rank-name: ' + yamlify(rank_name) + '\n')
    if(unit_name):
        f.write('unit: ' + yamlify(unit_name) + '\n')
        f.write('unit-id: ' + unit_id + '\n')
        f.write('unit-slug: ' + urlify(unit_name) + '\n')
    f.write('slug: ' + urlify(name) + '\n')
    if(force_name):
        f.write('force: ' + yamlify(force_name) + '\n')
        f.write('force-slug: ' + urlify(force_name) + '\n')
    if(portrait_path != '' and portrait_file != ''):
        new_portrait_file = replace_portrait_name(portrait_file, urlify(name))
        portrait_paths[new_portrait_file] = portrait_path
        f.write('portrait: ' + new_portrait_file + '\n')
    f.write('---\n\n')
    f.write(unescape(bio))
    f.close()
    people_written = people_written + 1

# loop through missions and scenarios. Use slugs to link scenarios
# to mission, but actually linking will be done by liquid
missions_written = 0
scenarios_written = 0
if(missions is not None):
    for mission in missions.findall('mission'):
        mission_name = find_first_text(mission, 'name')
        if(mission_name == ''):
            continue
        mission_type = find_first_text(mission, 'type')
        # in modern saves the type attribute holds the java class name
        if('.' in mission_type or mission_type.startswith('mekhq')):
            mission_type = ''
        mission_desc = find_first_text(mission, 'desc', 'description')
        mission_id = int(mission.attrib.get('id',
                         find_first_text(mission, 'id') or '0')) * 10
        mission_start = get_xml_date(find_first(mission, 'startDate'))
        mission_end = get_xml_date(find_first(mission, 'endDate'))
        mission_employer = find_first_text(mission, 'employer')
        mission_location = find_first_text(mission, 'planetName', 'systemId',
                                           'planetId')
        mission_status = find_first_text(mission, 'status')
        f = open('campaign/_missions/' + urlify(mission_name) + '.md', 'w',
                 encoding='utf-8')
        f.write('---\n')
        f.write('layout: mission\n')
        f.write('title: ' + yamlify(mission_name) + '\n')
        if(mission_start is not None):
            f.write('start-date: ' + mission_start.strftime('%Y-%m-%d') + '\n')
        if(mission_end is not None):
            f.write('end-date: ' + mission_end.strftime('%Y-%m-%d') + '\n')
        if(mission_type != ''):
            f.write('type: ' + yamlify(mission_type) + '\n')
        if(mission_employer != ''):
            f.write('employer: ' + yamlify(mission_employer) + '\n')
        if(mission_location != ''):
            f.write('location: ' + yamlify(mission_location) + '\n')
        if(mission_status != ''):
            f.write('status: ' + yamlify(mission_status_dict.get(
                mission_status, prettify_enum(mission_status))) + '\n')
        f.write('mission-order: ' + str(mission_id) + '\n')
        f.write('slug: ' + urlify(mission_name) + '\n')
        f.write('---\n\n')
        f.write(unescape(mission_desc))
        f.close()
        missions_written = missions_written + 1
        scenarios = mission.find('scenarios')
        if(scenarios is not None):
            for scenario in scenarios.findall('scenario'):
                scenario_name = find_first_text(scenario, 'name')
                if(scenario_name == ''):
                    continue
                scenario_desc = find_first_text(scenario, 'desc',
                                                'description')
                scenario_aar = find_first_text(scenario, 'report')
                scenario_date = get_xml_date(find_first(scenario, 'date'))
                scenario_status = find_first_text(scenario, 'status')
                f = open('campaign/_scenarios/' +
                         urlify(mission_name + ' ' + scenario_name) + '.md',
                         'w', encoding='utf-8')
                f.write('---\n')
                f.write('layout: mission\n')
                f.write('title: ' + yamlify(scenario_name) + '\n')
                if(scenario_date is not None):
                    f.write('date: ' + scenario_date.strftime('%Y-%m-%d') +
                            '\n')
                if(scenario_status != ''):
                    f.write('status: ' + yamlify(scenario_status_dict.get(
                        scenario_status, prettify_enum(scenario_status))) +
                        '\n')
                f.write('mission: ' + yamlify(mission_name) + '\n')
                f.write('mission-slug: ' + urlify(mission_name) + '\n')
                f.write('---\n\n')
                f.write(unescape(scenario_desc) + '\n')
                if(scenario_aar != ''):
                    f.write('\n##### After-Action Report\n\n')
                    f.write(unescape(scenario_aar))
                f.close()
                scenarios_written = scenarios_written + 1

# ----------------------------------------------------------------------------
# Copy over data from MekHQ
# ----------------------------------------------------------------------------

# copy over images
portraits_copied = 0
portrait_dirs = [mekhq_path + 'data/images/portraits/',
                 mekhq_path + 'userdata/data/images/portraits/']
for portrait_name in portrait_paths:
    portrait_path = portrait_paths[portrait_name]
    for portrait_dir in portrait_dirs:
        source = portrait_dir + portrait_path
        if(os.path.exists(source)):
            copyfile(source, 'assets/images/portraits/' + portrait_name)
            portraits_copied = portraits_copied + 1
            break

print('Wrote {} personnel, {} missions, {} scenarios, {} forces, and copied '
      '{} portraits.'.format(people_written, missions_written,
                             scenarios_written,
                             len(glob.glob('campaign/_forces/*.md')),
                             portraits_copied))
