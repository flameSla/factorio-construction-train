"""
construction_train
"""

import base64
import collections
import json
import zlib
import sys
import os
import argparse
import math


#############################################
def error(*args):
    print(*args, file=sys.stderr, flush=True)


#############################################
def debug(*args):
    if opt.d:
        print(*args, file=sys.stderr, flush=True)


#############################################
def add_dictionaries(a, b):
    # a = a + b
    for key, value in b.items():
        if key in a:
            a[key] += value
        else:
            a[key] = value


#############################################
def parse_blueprint(bp, necessary_items_for_construction):
    if 'blueprint_book' in bp:
        for blueprint in bp['blueprint_book']['blueprints']:
            debug('\nblueprint-book =============================')
            debug(blueprint)
            parse_blueprint(blueprint, necessary_items_for_construction)
    elif 'blueprint' in bp:
        debug('\nblueprint ==================================')
        debug('<<< parse_blueprint( bp )')
        for entity in bp['blueprint']['entities']:
            debug(entity)
            if entity['name'] == 'curved-rail':
                add_dictionaries(necessary_items_for_construction,
                                 {"rail": 4})
            elif entity["name"] == 'straight-rail':
                add_dictionaries(necessary_items_for_construction,
                                 {"rail": 1})
            else:
                add_dictionaries(necessary_items_for_construction,
                                 {entity["name"]: 1})
            if 'items' in entity:
                debug(entity['items'], '\t', type(entity['items']))
                add_dictionaries(necessary_items_for_construction,
                                 entity['items'])
        debug('---------------------------------------------------')


#############################################
def print_dict(a):
    for k, v in a.items():
        print('{} = {}'.format(k, v))
    print()


#############################################
def new_bp():
    bp = collections.OrderedDict()
    bp['blueprint'] = collections.OrderedDict()
    # bp['blueprint']['description'] = str()
    # bp['blueprint']['icons'] = list()
    # bp['blueprint']['icons'].append(dict([('signal',
    #                                        dict([('type', 'item'),
    #                                              ('name', 'rail')])),
    #                                       ('index', 1)]))
    bp['blueprint']['entities'] = list()
    # bp['blueprint']['tiles'] = list()
    # bp['blueprint']['schedules'] = list()
    bp['blueprint']['item'] = 'blueprint'
    bp['blueprint']['label'] = str()
    # bp['blueprint']['label_color']
    # bp['blueprint']['version'] = 281479275937792 ????

    return bp


################################################################
def bp_to_string(bp):
    json_str = json.dumps(bp,
                          separators=(",", ":"),
                          ensure_ascii=False).encode("utf8")
    exchange_str = '0' + base64.b64encode(zlib.compress(json_str,
                                                        9)).decode('utf-8')

    return exchange_str


################################################################
def get_a_position(x, y):
    return {'x': x, 'y': y}


#############################################
def new_entity(bp, name, pos_x, pos_y,
               direction=None,
               orientation=None):

    entity = dict()
    entity['entity_number'] = len(bp['blueprint']['entities']) + 1
    entity['name'] = name
    entity['position'] = get_a_position(pos_x, pos_y)
    if direction is not None:
        entity['direction'] = direction
    if orientation is not None:
        entity['orientation'] = orientation

    return entity


#############################################
def entity_add_items(entity, item):
    if 'items' in entity:
        entity['items'].update(item)
    else:
        entity['items'] = item


#############################################
def get_items():
    # read json file
    with open('items.json', 'r') as read_file:
        json_items = json.load(read_file)

    # json -> dist()
    items = dict()
    for i in json_items['items']:
        items[i['name']] = float(i['stack'])  # items["wooden-chest"] = 50.0

    return items


#############################################
def add_train(bp, train_number, locomotives, cars):
    train_car_position = 0

    train_length = (locomotives + cars)*7 - 1
    number_of_rails = math.ceil(train_length/2) + 2
    for i in range(number_of_rails):
        rail = new_entity(bp,
                          'straight-rail',
                          i*2 - 1,
                          train_number*4 + 1,
                          direction=2)
        bp['blueprint']['entities'].append(rail)

    for i in range(locomotives):
        locomotive = new_entity(bp,
                                'locomotive',
                                7 * train_car_position + 4,
                                train_number*4 + 1,
                                orientation=0.75)
        entity_add_items(locomotive, {'nuclear-fuel': 3})
        bp['blueprint']['entities'].append(locomotive)
        train_car_position += 1

    return train_car_position


#############################################
def get_bp(locomotives, cars, necessary_items_for_construction):
    # "item name": amount
    additional_items = {
        "construction-robot": 1350,
        "logistic-robot": 350,
        "radar": 50,
        "repair-pack": 100,
        "cliff-explosives": 100,
        "laser-turret": 50
    }

    print("additional items:")
    print_dict(additional_items)

    # contents = additional_items + necessary_items_for_construction
    contents = dict()
    add_dictionaries(contents, additional_items)
    add_dictionaries(contents, necessary_items_for_construction)

    bp = new_bp()
    items = get_items()

    train_number = 0
    train_car_position = add_train(bp, train_number, locomotives, cars)

    cargo_wagon = new_entity(bp,
                             'cargo-wagon',
                             7 * train_car_position + 4,
                             train_number*4 + 1,
                             orientation=0.75)

    slot_count = 0

    for item, amount in contents.items():
        stack_size = items[item]

        while amount > 0:
            slots = math.ceil(amount/stack_size)
            if slot_count + slots >= 40:
                add_items = (40 - slot_count) * stack_size
                amount -= add_items
                entity_add_items(cargo_wagon, dict([(item, add_items)]))
                # Add a new wagon
                train_car_position += 1
                if train_car_position >= locomotives+cars:
                    train_number += 1
                    train_car_position = add_train(bp,
                                                   train_number,
                                                   locomotives,
                                                   cars)

                bp['blueprint']['entities'].append(cargo_wagon)
                slot_count = 0
                cargo_wagon = new_entity(bp,
                                         'cargo-wagon',
                                         7 * train_car_position + 4,
                                         train_number*4 + 1,
                                         orientation=0.75)
            else:
                entity_add_items(cargo_wagon, dict([(item, amount)]))
                amount = 0
                slot_count += slots

    # Add the last wagon if we didn't exceed the inventory
    bp['blueprint']['entities'].append(cargo_wagon)

    bp['blueprint']['label_color'] = {"r": 1, "g": 0, "b": 1}
    bp['blueprint']['label'] = "{}-{} construction_train".format(locomotives,
                                                                 cars)

    print()
    print(bp_to_string(bp))


######################################
#
# main
if __name__ == "__main__":

    exchange_str = ''
    parser = argparse.ArgumentParser(
        description="example: python construction_train.py")
    parser.add_argument("-d", "--debug", action="store_true", dest="d",
                        help="debug output on STDERR")
    opt = parser.parse_args()

    locomotives = input('locomotives:')
    cars = input('cars:')
    exchange_str = input('bp to be built:(string or filename.txt)')
    if os.path.exists(exchange_str):
        with open(exchange_str, 'r') as f:
            exchange_str = f.read()

    version_byte = exchange_str[0]
    if version_byte == '0':
        json_str = zlib.decompress(base64.b64decode(exchange_str[1:]))
        bp_json = json.loads(json_str,
                             object_pairs_hook=collections.OrderedDict)

        necessary_items_for_construction = dict()
        parse_blueprint(bp_json, necessary_items_for_construction)
        print("bp contains:")
        print_dict(necessary_items_for_construction)

        get_bp(int(locomotives), int(cars), necessary_items_for_construction)

    else:
        error("Unsupported version: {0}".format(version_byte))
        exit(2)
