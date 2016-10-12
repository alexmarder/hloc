#!/usr/bin/env python3.5

import src.data_processing.util as util
import collections
import os


# Fix old wrong dataformat
# for i in range(0,8):
#     o_file = open('/data2/trie-results/router.domains-{}-found.checked'.format(i))
#     r_file = open('/data2/trie-results/router.domains-{}-found.checked.rep'.format(i), 'w')
#     for line in o_file:
#         domains = util.json_loads(line)
#         for domain in domains[util.DomainType.correct.value]:
#             domain.location_id = domain.matching_match.location_id
#         util.json_dump(domains, r_file)
#         r_file.write('\n')
#     o_file.close()
#     r_file.close()


# for i in range(0,8):
#     with open('/data2/trie-results/router.domains-{}-found.checked.rep'.format(i)) as file:
#         for line in file:
#             domains = util.json_loads(line)
#             for domain in domains[util.DomainType.correct.value]:
#                 if domain.location_id is None:
#                     print(domain.ip_address)
#                     print(domain.matching_match)
#                     print(domain.matching_match.location_id)
count_not_found = 0
for i in range(0,8):
    with open('/data2/trie-results/wip/router.domains-{}-found.json'.format(i)) as d_file:
        for line in d_file:
            count_not_found += len(util.json_loads(line))

ips = set()
for i in range(0,8):
    with open('/data2/trie-results/router.domains-{}-found.checked'.format(i)) as file:
        for line in file:
            domains = util.json_loads(line)
            for domain in domains[util.DomainType.no_verification.value]:
                ips.add(domain.ip_address)
            for domain in domains[util.DomainType.no_location.value]:
                ips.add(domain.ip_address)
with open('/data2/trie-results/not_verified.ips', 'w') as output_file:
    string_to_write = ''
    for ip in ips:
        string_to_write += '{}\n'.format(ip)
    _ = output_file.write(string_to_write)


def get_number_no_probe(no_probe_locations, filename_proto, ips):
    c_matches = 0
    c_u_matches = 0
    for i in range(0,8):
        with open(filename_proto.format(i)) as file:
            for line in file:
                domains_dict = util.json_loads(line)
                for domain in domains_dict[util.DomainType.no_verification.value]:
                    if not ips or domain.ip_address in ips:
                        for match in domain.possible_matches:
                            if str(match.location_id) in no_probe_locations:
                                c_matches += 1
                                if len(domain.possible_matches) == 1:
                                    c_u_matches += 1
    print(c_matches)
    print(c_u_matches)


ips = set()
with open('/data2/router-ip-filtered/cor-ips.data') as ip_file:
    for line in ip_file:
        ips.add(line.strip())


def split_zmap(filename, ip_version, ips):
    with open(filename) as file, \
            open(filename + '.wip', 'w') as w_ip_file, \
            open(filename + '.woip', 'w') as wo_ip_file:
        count_w_ip = 0
        count_wo_ip = 0
        results_w_ip = {}
        results_wo_ip = {}
        for line in file:
            results = json.loads(line)
            for ip, result in results.items():
                if ip in ips:
                    results_w_ip[ip] = result
                    count_w_ip += 1
                else:
                    results_wo_ip[ip] = result
                    count_wo_ip += 1
        json.dump(results_w_ip, w_ip_file)
        json.dump(results_wo_ip, wo_ip_file)
        print('w ip {}'.format(count_w_ip))
        print('wo ip {}'.format(count_wo_ip))

def get_stats_for_filenameproto(filename_proto):
    lens = collections.defaultdict(int)
    for i in range(0,8):
        with open(filename_proto.format(i)) as d_file:
            for line in d_file:
                domain_dict = util.json_loads(line)
                for key, value in domain_dict.items():
                    lens[key] += len(value)
    print(lens)

def get_code_stats_checked(filename_proto):
    stats_v = collections.defaultdict(int)
    stats_no_v = collections.defaultdict(int)
    stats_f = collections.defaultdict(int)
    for i in range(0,8):
        with open(filename_proto.format(i)) as d_file:
            for line in d_file:
                domain_dict = util.json_loads(line)
                for domains in domain_dict.values():
                    for domain in domains:
                        for match in domain.all_matches:
                            if match == domain.matching_match:
                                stats_v[match.code_type] += 1
                            else:
                                if match.possible:
                                    stats_no_v[match.code_type] += 1
                                else:
                                    stats_f[match.code_type] += 1
    print('verified {}'.format(stats_v))
    print('not verified {}'.format(stats_no_v))
    print('falsified {}'.format(stats_f))

def get_code_stats(filename_proto):
    stats = collections.defaultdict(int)
    for i in range(0,8):
        with open(filename_proto.format(i)) as d_file:
            for line in d_file:
                domain_list = util.json_loads(line)
                for domain in domain_list:
                    for match in domain.all_matches:
                        stats[match.code_type] += 1
    print(stats)

def get_clli_falsified(filename_proto):
    clli_domains = []
    for i in range(0,8):
        with open(filename_proto.format(i)) as d_file:
            for line in d_file:
                domain_dict = util.json_loads(line)
                for domain in domain_dict[util.DomainType.no_location.value]:
                    clli_matches = [match for match in domain.all_matches
                                    if match.code_type == util.LocationCodeType.clli]
                    if clli_matches:
                        clli_domains.append(domain)
    return clli_domains

def count_domains(filename_proto):
    count_d = 0
    for i in range(0,8):
        with open(filename_proto.format(i)) as d_file:
            for line in d_file:
                count_d += len(json.loads(line))
    print(count_d)


def collect_rtts(filename_proto):
    cor_rtts = []
    no_v_rtts = []
    for i in range(0, 8):
        with open(filename_proto.format(i)) as file:
            for line in file:
                domains = util.json_loads(line)
                for domain in domains[util.DomainType.correct.value]:
                    cor_rtts.append(domain.matching_match.matching_rtt)
                for domain in domains[util.DomainType.no_verification.value]:
                    rtts = [match.matching_rtt for match in domain.all_matches if match.matching_rtt and match.matching_rtt > 0]
                    if rtts:
                        no_v_rtts.append(min(rtts))
    with open(os.path.join(os.path.dirname(filename_proto), 'corr_rtts'), 'w') as output_file:
        wr_str = ''
        for rtt in cor_rtts:
            wr_str += '{}\n'.format(rtt)
        output_file.write(wr_str)
    with open(os.path.join(os.path.dirname(filename_proto), 'no_v_rtts'), 'w') as output_file:
        wr_str = ''
        for rtt in no_v_rtts:
            wr_str += '{}\n'.format(rtt)
        output_file.write(wr_str)
    print('cor avg {}  min {}   max {}'.format((sum(cor_rtts)/len(cor_rtts)), min(cor_rtts),
                                               max(cor_rtts)))
    print('nov avg {}  min {}   max {}'.format((sum(no_v_rtts) / len(no_v_rtts)), min(no_v_rtts),
                                               max(no_v_rtts)))


collect_rtts('/data2/trie-results/router.domains-{}-found.checked')

rtts=[]
with open('/data2/trie-results/corr_rtts') as rtt_file:
    for line in rtt_file:
        rtts.append(float(line.strip()))


def count_ips_v6():
    ips = []
    with open('/data2/router-ipv6-cleared/ipfiltered/cor-ips.data') as file:
        for line in file:
            ips.append(line.strip())
    u_ips = set(ips)
    print(len(ips))
    print(len(u_ips))
    a_ips = set()
    with open('/data/rdns-parse/ipv6-router.ips.announced') as ips_file:
        for line in ips_file:
            line = line.strip()
            a_ips.add(line)
    print('filtered {}'.format(len(u_ips) - len(u_ips.intersection(a_ips))))
    with open('/data/ipv6-zmap.results') as zmap_file:
        _ = zmap_file.readline()
        line = zmap_file.readline()
        results = util.json_loads(line)
    reachables = set(results.keys())
    # print(len(reachables))
    # print(len(u_ips.intersection(a_ips).intersection(reachables)))
    print('timeouts {}'.format(
        len(u_ips) - len(u_ips.intersection(a_ips).intersection(reachables)) - (
        len(u_ips) - len(u_ips.intersection(a_ips)))))


# file_name_v4 = '/data2/trie-results/router.domains-{}-found.json'
# file_name_v6 = '/data2/rdns-results-v6/ipv6_rdns-{}-found.json'
def count_ips():
    file_name = '/data2/router-ip-filtered/router.domains-{}.cor'
    ips = []

    for i in range(0, 8):
        with open(file_name.format(i)) as file:
            for line in file:
                domains = util.json_loads(line)
                ips.extend([domain.ip_address for domain in domains])
    u_ips = set(ips)
    print(len(u_ips))
    a_ips = set()
    with open('/data/scan-2016-07-15/dallas/router.ips.announced') as ips_file:
        for line in ips_file:
            line = line.strip()
            a_ips.add(line)
    print(len(u_ips.intersection(a_ips)))
    print('filtered {}'.format(len(u_ips) - len(u_ips.intersection(a_ips))))
    with open('/data/cleared-ipv4-results.zmap') as zmap_file:
        _ = zmap_file.readline()
        line = zmap_file.readline()
        results = util.json_loads(line)
    reachables = set(results.keys())
    # print(len(reachables))
    # print(len(u_ips.intersection(a_ips).intersection(reachables)))
    print('timeouts {}'.format(
        len(u_ips) - len(u_ips.intersection(a_ips).intersection(reachables)) - (
        len(u_ips) - len(u_ips.intersection(a_ips)))))
