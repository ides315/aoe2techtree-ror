#! /usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path

TECH_TREE_STRINGS = {
    "Age of Empires II": "1001",
    "Civilization": "9681",
    "Technology Tree": "9799",
    "Key": "300081",
    "Unique Unit": "300082",
    "Unit": "300083",
    "Building": "300084",
    "Technology": "300085",
}

AGE_NAMES = {
    "Stone Age": "4201",
    "Tool Age": "4202",
    "Bronze Age": "4203",
    "Iron Age": "4204"
}

CIV_NAMES = {
    "Egyptians": "310271",
    "Greeks": "310272",
    "Babylonians": "310273",
    "Assyrians": "310274",
    "Minoans": "310275",
    "Hittites": "310276",
    "Phoenicians": "310277",
    "Sumerians": "310278",
    "Persians": "310279",
    "Shang": "310280",
    "Yamato": "310281",
    "Choson": "310282",
    "Romans": "310283",
    "Carthaginians": "310284",
    "Palmyrans": "310285",
    "Macedonians": "310286",
    "Lac Viet": "310287",
}

CIV_HELPTEXTS = {
    "Egyptians": "120150",
    "Greeks": "120151",
    "Babylonians": "120152",
    "Assyrians": "120153",
    "Minoans": "120154",
    "Hittites": "120155",
    "Phoenicians": "120156",
    "Sumerians": "120157",
    "Persians": "120158",
    "Shang": "120159",
    "Yamato": "120160",
    "Choson": "120161",
    "Romans": "120162",
    "Carthaginians": "120163",
    "Palmyrans": "120164",
    "Macedonians": "120165",
    "Lac Viet": "120166",
}

BUILDING_STYLES = {
    "Egyptians": "3",
    "Greeks": "4",
    "Babylonians": "2",
    "Assyrians": "3",
    "Minoans": "4",
    "Hittites": "3",
    "Phoenicians": "4",
    "Sumerians": "2",
    "Persians": "2",
    "Shang": "1",
    "Yamato": "1",
    "Choson": "1",
    "Romans": "5",
    "Carthaginians": "5",
    "Palmyrans": "5",
    "Macedonians": "5",
    "Lac Viet": "1",
}

LANGUAGES = [
    'br',
    'de',
    'en',
    'es',
    'fr',
    'hi',
    'it',
    'jp',
    'ko',
    'ms',
    'mx',
    'pl',
    'ru',
    'tr',
    'tw',
    'vi',
    'zh',
]


def get_unit_cost(unit):
    return get_cost(unit["Creatable"])


def get_cost(creatable):
    cost = {}
    resource_costs = creatable["ResourceCosts"]
    for rc in resource_costs:
        if rc["Type"] == 0:
            cost["Food"] = rc["Amount"]
        if rc["Type"] == 1:
            cost["Wood"] = rc["Amount"]
        if rc["Type"] == 2:
            cost["Stone"] = rc["Amount"]
        if rc["Type"] == 3:
            cost["Gold"] = rc["Amount"]
    return cost


def gather_language_data(programdir, data, language):
    key_value = {}
    # some strings are shared with the base game; read these in first
    key_value_strings_file_en = programdir / 'resources' / language / 'strings' / 'key-value' / 'key-value-strings-utf8.txt'
    with key_value_strings_file_en.open(encoding='utf-8') as f:
        for line in f:
            parse_line(key_value, line)
    # override strings with everything specific to AoE1 / Return of Rome
    key_value_pompeii_strings_file_en = programdir / 'modes' / 'Pompeii' / 'resources' / language / 'strings' / 'key-value' / 'key-value-pompeii-strings-utf8.txt'
    with key_value_pompeii_strings_file_en.open(encoding='utf-8') as f:
        for line in f:
            parse_line(key_value, line)

    key_value[5121] = key_value[305131]     #  Villager
    key_value[26121] = key_value[326131]

    key_value[305471] = key_value[305470]   #  Trade Cart
    key_value[326471] = key_value[326470]


    key_value_filtered = {}
    for datatype in ("buildings", "units", "techs"):
        for item_id in data[datatype]:
            name_id = data[datatype][item_id]['LanguageNameId']
            help_id = data[datatype][item_id]['LanguageHelpId']
            key_value_filtered[name_id] = key_value[name_id]
            key_value_filtered[help_id] = key_value[help_id]
            
    for name in CIV_HELPTEXTS:
        key = int(CIV_HELPTEXTS[name])
        key_value_filtered[key] = key_value[key]
    for name in CIV_NAMES:
        key = int(CIV_NAMES[name])
        key_value_filtered[key] = key_value[key]
    for name in AGE_NAMES:
        key = int(AGE_NAMES[name])
        key_value_filtered[key] = key_value[key]
    for name in TECH_TREE_STRINGS:
        key = int(TECH_TREE_STRINGS[name])
        key_value_filtered[key] = key_value[key]
    return key_value_filtered


def parse_line(key_value, line):
    items = line.split(" ")
    if items[0].isnumeric():
        number = int(items[0])
        match = re.search('".+"', line)
        if match:
            text = match.group(0)[1:-1]
            text = re.sub(r'<(.+?)>', r'‹\1›', text)
            text = re.sub(r'‹b›(.+?)‹b›', r'<b>\1</b>', text)
            text = re.sub(r'‹i›(.+?)‹i›', r'<i>\1</i>', text)
            text = re.sub(r'\\n', r'<br>\n', text)
            key_value[number] = text


def gather_data(content, civs, unit_upgrades):
    ages = list(AGE_NAMES.keys())[1:]
    building_ids = {b for c in civs.values() for b in c['buildings']}
    unit_ids = {u for c in civs.values() for u in c['units']}
    tech_ids = set.union(
        {t for c in civs.values() for t in c['techs']},
        {t for t, tech in enumerate(content['Techs']) if tech['Name'] in ages},
        {t for t, tech in enumerate(content['Techs']) if 'Wall' in tech['Name']},
        {t for t, tech in enumerate(content['Techs']) if 'Tower' in tech['Name']},
        {49},  # archer chain mail
    )
    gaia = content["Civs"][0]
    graphics = content["Graphics"]
    data = {"buildings": {}, "units": {}, "techs": {}, "unit_upgrades": {}}
    for unit in gaia["Units"]:
        if unit["ID"] in building_ids:
            add_building(unit["ID"], unit, data)
        if unit["ID"] in unit_ids:
            add_unit(unit["ID"], unit, graphics, data)
    tech_id = 0
    for tech in content["Techs"]:
        if tech_id in tech_ids:
            add_tech(tech_id, tech, data)
        tech_id += 1

    for unit_id, upgrade_id in unit_upgrades.items():
        tech = content["Techs"][upgrade_id]
        add_unit_upgrade(unit_id, tech_id, tech, data)

    return data


def add_building(building_id, unit, data):
    data['buildings'][building_id] = {
        'internal_name': unit['Name'],
        'ID': building_id,
        'HP': unit["HitPoints"],
        'Cost': get_unit_cost(unit),
        'Attack': unit["Type50"]["DisplayedAttack"],
        'Range': unit["Type50"]["DisplayedRange"],
        'MeleeArmor': unit["Type50"]["DisplayedMeleeArmour"],
        'PierceArmor': unit["Creatable"]["DisplayedPierceArmour"],
        'GarrisonCapacity': unit["GarrisonCapacity"],
        'LineOfSight': unit["LineOfSight"],
        'Attacks': unit["Type50"]["Attacks"],
        'Armours': unit["Type50"]["Armours"],
        'ReloadTime': unit["Type50"]["ReloadTime"],
        'AccuracyPercent': unit["Type50"]["AccuracyPercent"],
        'MinRange': unit["Type50"]["MinRange"],
        'TrainTime': unit["Creatable"]["TrainTime"],
        'LanguageNameId': unit['LanguageDLLName'],
        'LanguageHelpId': unit['LanguageDLLName'] + 21_000,
    }


def add_unit(key, unit, graphics, data):
    if unit["Type50"]["FrameDelay"] == 0 or unit["Type50"]["AttackGraphic"] == -1:
        attack_delay_seconds = 0.0
    else:
        attack_graphic = graphics[unit["Type50"]["AttackGraphic"]]
        animation_duration = attack_graphic["AnimationDuration"]
        frame_delay = unit["Type50"]["FrameDelay"]
        frame_count = attack_graphic["FrameCount"]
        attack_delay_seconds = animation_duration * frame_delay / frame_count
    data['units'][key] = {
        'internal_name': unit['Name'],
        'ID': key,
        'HP': unit["HitPoints"],
        'Cost': get_unit_cost(unit),
        'Attack': unit["Type50"]["DisplayedAttack"],
        'Range': unit["Type50"]["DisplayedRange"],
        'MeleeArmor': unit["Type50"]["DisplayedMeleeArmour"],
        'PierceArmor': unit["Creatable"]["DisplayedPierceArmour"],
        'GarrisonCapacity': unit["GarrisonCapacity"],
        'LineOfSight': unit["LineOfSight"],
        'Speed': unit["Speed"],
        'Trait': unit["Trait"],
        'TraitPiece': unit["Nothing"],
        'Attacks': unit["Type50"]["Attacks"],
        'Armours': unit["Type50"]["Armours"],
        'ReloadTime': unit["Type50"]["ReloadTime"],
        'AccuracyPercent': unit["Type50"]["AccuracyPercent"],
        'FrameDelay': unit["Type50"]["FrameDelay"],
        'AttackDelaySeconds': attack_delay_seconds,
        'MinRange': unit["Type50"]["MinRange"],
        'TrainTime': unit["Creatable"]["TrainTime"],
        'MaxCharge': unit["Creatable"]["MaxCharge"],
        'RechargeRate': unit["Creatable"]["RechargeRate"],
        'ChargeEvent': unit["Creatable"]["ChargeEvent"],
        'ChargeType': unit["Creatable"]["ChargeType"],
        'LanguageNameId': unit['LanguageDLLName'],
        'LanguageHelpId': unit['LanguageDLLName'] + 21_000,
    }
    if unit["Creatable"]["RechargeRate"] > 0:
        data['units'][key]['RechargeDuration'] = unit["Creatable"]["MaxCharge"] / unit["Creatable"]["RechargeRate"]


def add_tech(key, tech, data):
    data['techs'][key] = {
        'internal_name': tech['Name'],
        'ResearchTime': tech['ResearchTime'],
        'ID': key,
        'Cost': get_cost(tech),
        'LanguageNameId': tech['LanguageDLLName'],
        'LanguageHelpId': tech['LanguageDLLName'] + 21_000,
        'Repeatable': tech['Repeatable'] == "1",
    }


def add_unit_upgrade(key, tech_id, tech, data):
    data['unit_upgrades'][key] = {
        'internal_name': tech['Name'],
        'ResearchTime': tech['ResearchTime'],
        'ID': tech_id,
        'Cost': get_cost(tech),
    }


def is_unit(unit):
    is_unit_type = (unit.get('Node Type') in ('Unit', 'UnitUpgrade'))
    is_available = (unit.get('Node Status', 'NotAvailable') != 'NotAvailable')
    return (is_unit_type and is_available)


def is_tech(tech):
    is_tech_type = (tech.get('Node Type') == 'Research')
    is_available = (tech.get('Node Status', 'NotAvailable') != 'NotAvailable')
    return (is_tech_type and is_available)


def gather_civs(techtrees):
    unit_excludelist = ()
    civs = {}
    unit_upgrades = {}
    for civ in techtrees['civs']:
        current_civ = {'buildings': [], 'units': [], 'techs': []}
        for building in civ['civ_techs_buildings']:
            if building['Node Status'] != 'NotAvailable':
                current_civ['buildings'].append(building['Node ID'])
        for unit in filter(is_unit, civ['civ_techs_units']):
            current_civ['units'].append(unit['Node ID'])
            if unit['Trigger Tech ID'] > -1:
                unit_upgrades[unit['Node ID']] = unit['Trigger Tech ID']
        for tech in filter(is_tech, civ['civ_techs_units']):
            current_civ['techs'].append(tech['Node ID'])

        current_civ['buildings'] = sorted(current_civ['buildings'])
        current_civ['units'] = sorted(current_civ['units'])
        current_civ['techs'] = sorted(current_civ['techs'])

        civname = civ['civ_id'].capitalize()
        if civname == 'Carthagians':
            civname = 'Carthaginians'   # correct spelling; Carthag_IN_ians
        elif civname == 'Lacviet':
            civname = 'Lac Viet'        # add space
        civs[civname] = current_civ

    return civs, unit_upgrades


def update_civ_techs(civs, data):
    age_ups = [t['ID'] for t in data['techs'].values()
               if t['internal_name'].endswith('Age')]
    wall_tower_techs = {
        72: 11,  #  Small Wall
        117: 13, #  Medium Wall
        155: 14, #  Fortified Wall
        79: 16,  #  Watch Tower
        234: 12, #  Sentry Tower
        235: 15, #  Guard Tower
        236: 2,  #  Ballista Tower
    }
    for civ in civs.values():
        civ['techs'].extend(age_ups)
        for building_id, tech_id in wall_tower_techs.items():
            if building_id in civ['buildings']:
                civ['techs'].append(tech_id)
        civ['techs'].sort()


def write_datafile(data, techtrees, outputdir):
    datafile = outputdir / 'data.json'
    data = {
        "age_names": AGE_NAMES,
        "building_styles": BUILDING_STYLES, 
        "civ_helptexts": CIV_HELPTEXTS,
        "civ_names": CIV_NAMES,
        "data": data,
        "tech_tree_strings": TECH_TREE_STRINGS,
        "techtrees": techtrees,
    }
    with datafile.open('w') as f:
        print(f'Writing data file {datafile}')
        json.dump(data, f, indent=4, sort_keys=True, ensure_ascii=False)


def write_language_files(args, data, outputdir):
    programdir = Path(args.programdir)
    for language in LANGUAGES:
        key_value_filtered = gather_language_data(programdir, data, language)

        languagedir = outputdir / 'locales' / language
        languagedir.mkdir(parents=True, exist_ok=True)
        languagefile = languagedir / 'strings.json'
        with languagefile.open('w', encoding='utf-8') as f:
            print(f'Writing language file {languagefile}')
            json.dump(key_value_filtered, f, indent=4, sort_keys=True, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Generate data files for aoe2techtree')
    parser.add_argument('datafile', help='A full.json file generated by aoe2dat')
    parser.add_argument('programdir', help='The main folder of an aoe2de installation, usually '
                                           'C:/Program Files (x86)/Steam/steamapps/common/AoE2DE/')
    parser.add_argument('--output', help='The data directory to place the output files into')

    args = parser.parse_args()

    if args.output and not Path(args.output).is_dir():
        print(f'The output path {args.output} is not an existing directory.')
        sys.exit()

    outputdir = Path(__file__).parent / '..' / 'data'
    if args.output:
        outputdir = Path(args.output)

    techtreesfile = Path(args.programdir) / 'modes' / 'Pompeii' / 'resources' / '_common' / 'dat' / 'civTechTrees.json'
    techtrees = json.loads(techtreesfile.read_text())
    civs, unit_upgrades = gather_civs(techtrees)

    datafile = Path(args.datafile)
    content = json.loads(datafile.read_text())
    data = gather_data(content, civs, unit_upgrades)

    update_civ_techs(civs, data)

    write_datafile(data, civs, outputdir)
    write_language_files(args, data, outputdir)


if __name__ == '__main__':
    main()
