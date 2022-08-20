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
import uuid


#############################################
def error(*args):
    print(*args, file=sys.stderr, flush=True)


#############################################
def debug(*args):
    if opt.d:
        print(*args, file=sys.stderr, flush=True)


#############################################
class dict_bp(dict):

    def __add__(self, other):
        temp = dict_bp(self)
        for key, value in other.items():
            if key in temp:
                temp[key] += value
            else:
                temp[key] = value
        return temp

    def __iadd__(self, other):
        for key, value in other.items():
            if key in self:
                self[key] += value
            else:
                self[key] = value
        return self


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
                necessary_items_for_construction += {"rail": 4}
            elif entity["name"] == 'straight-rail':
                necessary_items_for_construction += {"rail": 1}
            else:
                necessary_items_for_construction += {entity["name"]: 1}
            if 'items' in entity:
                debug(entity['items'], '\t', type(entity['items']))
                necessary_items_for_construction += entity['items']
        if 'tiles' in bp['blueprint']:
            for tile in bp['blueprint']['tiles']:
                necessary_items_for_construction += {tile['name']: 1}

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
    bp['blueprint']['icons'] = list()
    bp['blueprint']['icons'].append(dict([('signal',
                                         dict([('type', 'virtual'),
                                               ('name', 'signal-B')])),
                                          ('index', 1)]))
    bp['blueprint']['entities'] = list()
    # bp['blueprint']['tiles'] = list()
    # bp['blueprint']['schedules'] = list()
    bp['blueprint']['item'] = 'blueprint'
    bp['blueprint']['label'] = str()
    # bp['blueprint']['label_color']
    bp['blueprint']['version'] = 281479275937792

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
def set_inventory_filter(entity, filtr):
    if 'inventory' not in entity:
        entity['inventory'] = dict()

    if 'filters' not in entity['inventory']:
        entity['inventory']['filters'] = list()

    entity['inventory']['filters'].append(filtr)


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
def add_train(bp, train_number, locomotives, cars, station_name):
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

    train_stop = new_entity(bp,
                            'train-stop',
                            7 * train_car_position + 1,
                            train_number*4 - 1,
                            direction=6)
    train_stop['station'] = station_name
    bp['blueprint']['entities'].append(train_stop)

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
def add_wagon(bp, train_car_position, train_number):
    return new_entity(bp,
                      'cargo-wagon',
                      7 * train_car_position + 4,
                      train_number*4 + 1,
                      orientation=0.75)


#############################################
def wagon_close_slots(cargo_wagon, slot_count):
    if slot_count < 40:
        cargo_wagon['inventory']['bar'] = slot_count
    while slot_count < 40:
        set_inventory_filter(cargo_wagon,
                             {"index": slot_count + 1, "name": "linked-chest"})
        slot_count += 1


#############################################
def append_chests(bp, filtrs, train_car_position, train_number, items):
    pos = 0
    for key, val in filtrs.items():
        inserter = new_entity(bp,
                              'stack-inserter',
                              7 * train_car_position + 1.5 + pos,
                              train_number*4 - 0.5)
        bp['blueprint']['entities'].append(inserter)

        requester = new_entity(bp,
                               'logistic-chest-requester',
                               7 * train_car_position + 1.5 + pos,
                               train_number*4 - 1.5)
        requester['request_filters'] = list()
        requester['request_filters'].append({"index": 1,
                                             "name": key,
                                             "count": items[key]})
        requester['request_from_buffers'] = 'true'
        bp['blueprint']['entities'].append(requester)

        pos += 1
    filtrs.clear()


#############################################
def requester_trains(bp, contents, train_number, train_car_position,
                     locomotives, cars, station_name):

    cargo_wagon = add_wagon(bp, train_car_position, train_number)

    slot_count = 0
    items = get_items()
    for item, amount in contents.items():
        stack_size = items[item]

        if item == 'landfill':
            bp['blueprint']['entities'].append(cargo_wagon)
            train_number += 1
            train_car_position = add_train(bp,
                                           train_number,
                                           locomotives,
                                           cars,
                                           station_name)
            slot_count = 0
            cargo_wagon = add_wagon(bp, train_car_position, train_number)

        while amount > 0:
            slots = math.ceil(amount/stack_size)
            if slot_count + slots >= 40:
                add_items = (40 - slot_count) * stack_size
                amount -= add_items
                entity_add_items(cargo_wagon, dict([(item, add_items)]))
                # Add a new wagon
                train_car_position += 1
                if train_car_position >= locomotives + cars:
                    train_number += 1
                    train_car_position = add_train(bp,
                                                   train_number,
                                                   locomotives,
                                                   cars,
                                                   station_name)

                bp['blueprint']['entities'].append(cargo_wagon)
                slot_count = 0
                cargo_wagon = add_wagon(bp, train_car_position, train_number)

            else:
                entity_add_items(cargo_wagon, dict([(item, amount)]))
                amount = 0
                slot_count += slots

    bp['blueprint']['entities'].append(cargo_wagon)


#############################################
def filtered_train(bp, contents, train_number, train_car_position,
                   locomotives, cars, station_name):

    cargo_wagon = add_wagon(bp, train_car_position, train_number)

    slot_count = 0
    filtrs = dict_bp()
    items = get_items()
    for item, amount in contents.items():
        stack_size = items[item]
        slots = math.ceil(amount/stack_size)

        if item == 'landfill':
            wagon_close_slots(cargo_wagon, slot_count)
            append_chests(bp, filtrs,
                          train_car_position, train_number, items)
            bp['blueprint']['entities'].append(cargo_wagon)
            train_number += 1
            train_car_position = add_train(bp,
                                           train_number,
                                           locomotives,
                                           cars,
                                           station_name)
            slot_count = 0
            cargo_wagon = add_wagon(bp, train_car_position, train_number)

        for _ in range(slots):
            new_item = item not in filtrs
            if slot_count >= 40 or (len(filtrs) >= 6 and new_item):
                # Add a new wagon
                wagon_close_slots(cargo_wagon, slot_count)
                append_chests(bp, filtrs,
                              train_car_position, train_number, items)

                train_car_position += 1
                if train_car_position >= locomotives + cars:
                    train_number += 1
                    train_car_position = add_train(bp,
                                                   train_number,
                                                   locomotives,
                                                   cars,
                                                   station_name)

                bp['blueprint']['entities'].append(cargo_wagon)
                slot_count = 0
                cargo_wagon = add_wagon(bp, train_car_position, train_number)

            set_inventory_filter(cargo_wagon,
                                 {"index": slot_count + 1, "name": item})
            filtrs += {item: 1}

            slot_count += 1

    wagon_close_slots(cargo_wagon, slot_count)
    append_chests(bp, filtrs, train_car_position, train_number, items)

    bp['blueprint']['entities'].append(cargo_wagon)


#############################################
def get_bp(locomotives, cars, necessary_items_for_construction):
    # "item name": amount
    additional_items = dict_bp({
        "construction-robot": 1350,
        "logistic-robot": 350,
        "radar": 50,
        "repair-pack": 100,
        "cliff-explosives": 100,
        "laser-turret": 50
    })

    print("additional items:")
    print_dict(additional_items)

    contents = additional_items + necessary_items_for_construction

    bp = new_bp()

    train_number = 0
    station_name = str(uuid.uuid4())
    train_car_position = add_train(bp, train_number,
                                   locomotives, cars, station_name)

    print("1 - requester trains")
    print("2 - filtered train")
    print("?")

    choise = int(input())
    if choise == 1:
        requester_trains(bp, contents, train_number, train_car_position,
                         locomotives, cars, station_name)
    elif choise == 2:
        filtered_train(bp, contents, train_number, train_car_position,
                       locomotives, cars, station_name)

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

        necessary_items_for_construction = dict_bp()
        parse_blueprint(bp_json, necessary_items_for_construction)
        print("bp contains:")
        print_dict(necessary_items_for_construction)

        get_bp(int(locomotives), int(cars), necessary_items_for_construction)

    else:
        error("Unsupported version: {0}".format(version_byte))
        exit(2)
