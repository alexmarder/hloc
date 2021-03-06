#!/usr/bin/env python3
"""The basic location object and all related inherited objects"""

import math

import hashlib
import sqlalchemy as sqla
import sqlalchemy.orm as sqlorm
import string
from sqlalchemy.dialects import postgresql

from hloc import constants
from .enums import LocationCodeType, AvailableType
from .sql_alchemy_base import Base


class AirportInfo(Base):
    """Holds a list of the different airport codes"""

    __tablename__ = 'airport_infos'

    id = sqla.Column(sqla.Integer, primary_key=True)
    iata_codes = sqla.Column(postgresql.ARRAY(sqla.String(3)), default=[], nullable=False)
    icao_codes = sqla.Column(postgresql.ARRAY(sqla.String(4)), default=[], nullable=False)
    faa_codes = sqla.Column(postgresql.ARRAY(sqla.String(5)), default=[], nullable=False)

    def __init__(self):
        self.iata_codes = []
        self.icao_codes = []
        self.faa_codes = []


class LocodeInfo(Base):
    """Holds a list of locode codes"""

    __tablename__ = 'locode_infos'

    id = sqla.Column(sqla.Integer, primary_key=True)
    place_codes = sqla.Column(postgresql.ARRAY(sqla.String(6)), default=[], nullable=False)
    subdivision_codes = sqla.Column(postgresql.ARRAY(sqla.String(6)), default=[], nullable=False)

    def __init__(self):
        self.place_codes = []
        self.subdivision_codes = []


class State(Base):
    __tablename__ = 'states'

    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String(50))
    iso3166code = sqla.Column(sqla.String(5), nullable=False)

    location_infos = sqlorm.relationship("LocationInfo", back_populates="state", cascade="all")


class Location(Base):
    """
    Basic class
    just contains the coordinates
    """

    __tablename__ = 'locations'

    id = sqla.Column(sqla.String(32), primary_key=True)
    lat = sqla.Column(sqla.Float, nullable=False)
    lon = sqla.Column(sqla.Float, nullable=False)

    probes = sqlorm.relationship('Probe', back_populates='location')

    location_type = sqla.Column(sqla.String)

    __mapper_args__ = {
        'polymorphic_identity': 'basic_location',
        'polymorphic_on': location_type
    }

    class PropertyKey:
        id = '0'
        lat = '1'
        lon = '2'

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        self.idfy_location()

    def available_probes(self, ip_versions: [str]):
        """
        :return: the available probes for this location
        """
        ip_versions_needed = []
        if constants.IPV4_IDENTIFIER in ip_versions and constants.IPV6_IDENTIFIER in ip_versions:
            ip_versions_needed.append(AvailableType.both_available)
        elif constants.IPV4_IDENTIFIER in ip_versions:
            ip_versions_needed.append(AvailableType.ipv4_available)
        elif constants.IPV6_IDENTIFIER in ip_versions:
            ip_versions_needed.append(AvailableType.ipv6_available)
        else:
            raise ValueError('no valid ip version in ip versions list')

        sorted_prbs = sorted(self.probes,
                             key=lambda probe: self.gps_distance_haversine(probe.location))
        return [probe for probe in sorted_prbs if probe.available() in ip_versions_needed][:25]

    def idfy_location(self):
        """
        Assign a unique id to every location in the array by computing the hash over all codes
        sorted alphabetically. That should guarantee a unique and
        """
        self.id = hashlib.md5('{}:{}'.format(self.lat, self.lon).encode()).hexdigest()

    def is_in_radius(self, location, radius):
        """Returns a True if the location is within the radius [km] with the haversine method"""
        return self.gps_distance_haversine(location) <= radius

    def gps_distance_equirectangular(self, location):
        """Return the distance between the two locations using the equirectangular method"""
        lon1 = math.radians(self.lon)
        lat1 = math.radians(self.lat)
        lon2 = math.radians(location.lon)
        lat2 = math.radians(location.lat)

        return math.sqrt((((lon2 - lon1) * math.cos(0.5 * (lat2 + lat1))) ** 2 + (
            lat2 - lat1) ** 2)) * constants.EARTH_RADIUS

    def gps_distance_haversine(self, location2):
        """
        Calculate the distance (km) between two points
        on the earth (specified in decimal degrees)
        """
        return self.gps_distance_haversine_plain(location2.lat, location2.lon)

    def gps_distance_haversine_plain(self, lat, lon):
        # convert decimal degrees to radians
        lon1 = math.radians(self.lon)
        lat1 = math.radians(self.lat)
        lon2 = math.radians(lon)
        lat2 = math.radians(lat)
        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        tmp = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        ftmp = 2 * math.asin(math.sqrt(tmp))
        # Radius of earth in kilometers. Use 3956 for miles
        return ftmp * constants.EARTH_RADIUS

    def location_with_distance_and_bearing(self, distance: float, bearing: float):
        """
        Calculate a new Location with the distance from this location in km and in
        direction of bearing
        :param distance: the distance in km
        :param bearing: the bearing in degrees 0 is north and it goes counter clockwise
        :return: a new location in direction of bearing with the distance
        """
        bearing_rad = math.radians(bearing)
        angular_dist = distance / constants.EARTH_RADIUS
        lat_rad = math.radians(self.lat)
        lon_rad = math.radians(self.lon)

        lat_new = math.asin(math.sin(lat_rad) * math.cos(angular_dist) +
                            math.cos(lat_rad) * math.sin(angular_dist) * math.cos(bearing_rad))
        lon_new_temp = math.atan2(
            math.sin(bearing_rad) * math.sin(angular_dist) * math.cos(lat_rad),
            math.cos(angular_dist) - math.sin(lat_rad) * math.sin(lat_new))
        lon_new = ((lon_rad - lon_new_temp + math.pi) % (2 * math.pi)) - math.pi

        return math.degrees(lat_new), math.degrees(lon_new)

    def __hash__(self):
        return hash(self.id)


probe_location_info_table = sqla.Table('probe_location_infos', Base.metadata,
                                       sqla.Column('probe_id', sqla.Integer,
                                                   sqla.ForeignKey('probes.id',
                                                                   ondelete='cascade')),
                                       sqla.Column('location_info_id', sqla.String(32),
                                                   sqla.ForeignKey('locations.id',
                                                                   ondelete='cascade')))


class LocationInfo(Location):
    """
    A location object with the location name, coordinates and location codes
    Additionally information like the population can be saved
    """

    __mapper_args__ = {'polymorphic_identity': 'location_infos'}

    city_name = sqla.Column(sqla.String(100))
    state_id = sqla.Column(sqla.Integer, sqla.ForeignKey(State.id))
    population = sqla.Column(sqla.Integer)
    airport_info_id = sqla.Column(sqla.Integer,
                                  sqla.ForeignKey(AirportInfo.id, ondelete='set null'))
    locode_info_id = sqla.Column(sqla.Integer,
                                 sqla.ForeignKey(LocodeInfo.id, ondelete='set null'))
    clli = sqla.Column(postgresql.ARRAY(sqla.String(6)), default=[])
    alternate_names = sqla.Column(postgresql.ARRAY(sqla.String(100)), default=[])

    state = sqlorm.relationship(State, back_populates='location_infos', cascade="all")
    nearby_probes = sqlorm.relationship('Probe',
                                        secondary=probe_location_info_table,
                                        back_populates='location_infos')
    airport_info = sqlorm.relationship(AirportInfo)
    locode_info = sqlorm.relationship(LocodeInfo)

    def __init__(self, lat: float, lon: float, **kwargs):
        self.clli = []
        self.alternate_names = []

        for name, value in kwargs.items():
            setattr(self, name, value)

        super().__init__(lat, lon)

    @property
    def name(self):
        return self.city_name

    @name.setter
    def name(self, name):
        self.city_name = name[:100]

    def available_probes(self, ip_versions: [str]):
        ip_versions_needed = []
        if constants.IPV4_IDENTIFIER in ip_versions and constants.IPV6_IDENTIFIER in ip_versions:
            ip_versions_needed.append(AvailableType.both_available)
        elif constants.IPV4_IDENTIFIER in ip_versions:
            ip_versions_needed.append(AvailableType.ipv4_available)
        elif constants.IPV6_IDENTIFIER in ip_versions:
            ip_versions_needed.append(AvailableType.ipv6_available)
        else:
            raise ValueError('no valid ip version in ip versions list')

        sorted_prbs = sorted(self.nearby_probes,
                             key=lambda probe: self.gps_distance_haversine(probe.location))
        return [probe for probe in sorted_prbs if probe.available() in ip_versions_needed][:25]

    def add_airport_info(self):
        """Creates and sets a new empty AirportInfo object"""
        if self.airport_info is None:
            self.airport_info = AirportInfo()

    def add_locode_info(self):
        """Creates and sets a new empty """
        if self.locode_info is None:
            self.locode_info = LocodeInfo()

    def code_id_type_tuples(self):
        """
        Creates a list with all codes in a tuple with the location id
        ONLY FOR TRIE CREATION
        :rtype: list(tuple)
        """
        # if not isinstance(self.id, int):
        #     print(self.dict_representation(), 'has no id')
        #     raise ValueError('id is not int')
        ret_list = []
        if self.city_name \
                and not set(self.city_name).difference(set(string.ascii_letters + string.digits)):
            ret_list.append((self.city_name.lower(), (self.id, LocationCodeType.geonames.value)))
        for code in self.clli:
            ret_list.append((code.lower(), (self.id, LocationCodeType.clli.value)))
        for name in self.alternate_names:
            if name:
                ret_list.append((name.lower(), (self.id, LocationCodeType.geonames.value)))
        if self.locode_info and self.state.iso3166code:
            for code in self.locode_info.place_codes:
                ret_list.append(('{}{}'.format(self.state.iso3166code.lower(), code.lower()),
                                 (self.id, LocationCodeType.locode.value)))
        if self.airport_info:
            for code in self.airport_info.iata_codes:
                ret_list.append((code.lower(), (self.id, LocationCodeType.iata.value)))
            for code in self.airport_info.icao_codes:
                ret_list.append((code.lower(), (self.id, LocationCodeType.icao.value)))
            for code in self.airport_info.faa_codes:
                ret_list.append((code.lower(), (self.id, LocationCodeType.faa.value)))
        return ret_list


domain_location_hints_table = sqla.Table('domain_location_hints', Base.metadata,
                                         sqla.Column('location_hint_id', sqla.Integer,
                                                     sqla.ForeignKey('location_hints.id',
                                                                     ondelete='cascade')),
                                         sqla.Column('domain_id', sqla.Integer,
                                                     sqla.ForeignKey('domains.id',
                                                                     ondelete='cascade')))


location_hint_label_table = sqla.Table('location_hint_labels', Base.metadata,
                                       sqla.Column('location_hint_id', sqla.Integer,
                                                   sqla.ForeignKey('location_hints.id',
                                                                   ondelete='cascade'),
                                                   primary_key=True),
                                       sqla.Column('domain_label_id', sqla.Integer,
                                                   sqla.ForeignKey('domain_labels.id',
                                                                   ondelete='cascade'),
                                                   primary_key=True))


class LocationHint(Base):
    """
    Connection class between Locations and Domains
    Represents a possible location of a domain
    """

    __tablename__ = 'location_hints'

    id = sqla.Column(sqla.Integer, primary_key=True)
    location_id = sqla.Column(sqla.String(32), sqla.ForeignKey(Location.id))

    location = sqlorm.relationship(Location, cascade='all')
    domains = sqlorm.relationship('Domain',
                                  secondary=domain_location_hints_table,
                                  back_populates='hints')
    labels = sqlorm.relationship("DomainLabel",
                                 secondary=location_hint_label_table,
                                 back_populates="hints")

    hint_type = sqla.Column(sqla.String)

    __mapper_args__ = {
        'polymorphic_identity': 'basic_location_hint',
        'polymorphic_on': hint_type
    }


__all__ = ['AirportInfo',
           'LocodeInfo',
           'State',
           'Location',
           'LocationInfo',
           'location_hint_label_table',
           'probe_location_info_table',
           ]
