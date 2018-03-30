#!/usr/bin/python
#
# Copyright 2018 Jigsaw Operations LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import ipaddress
import pprint
import socket

import ipywidgets as widgets

from netanalysis.dns import domain_ip_validator
from netanalysis.ip import ip_info as ii
from netanalysis.ip import model


VALIDATOR = domain_ip_validator.DomainIpValidator()


def create_ip_info_widget(ip_info: ii.IpInfoService):
    ip_field = widgets.Text(placeholder="Enter ip address", description="IP")
    get_btn = widgets.Button(description="Get info")
    output = widgets.Output()

    def show_ip_info(_):
        output.clear_output()
        if not ip_field.value:
            return
        try:
            ip_address = ipaddress.ip_address(ip_field.value)
        except ValueError as e:
            with output:
                print("Invalid IP: %s" % ip_field.value)
                return
        asys = ip_info.get_as(ip_address)  # type: model.AutonomousSytem
        with output:
            print("ASN:  %d (%s)" % (asys.id, asys.name))
            # AS Type is is experimental and outdated data.
            print("Type: %s" % asys.type.name)
            print("Org:  %s (country: %s, name: %s)" %
                  (asys.org.id, asys.org.country, asys.org.name))
            if ip_address.is_global:
                hostname = ip_info.resolve_ip(ip_address)
                if hostname:
                    print("Hostname: %s" % hostname)
            else:
                print("IP is not global")
            try:
                cert = asyncio.get_event_loop().run_until_complete(
                    VALIDATOR.get_cert(None, ip_address))
                if cert:
                    print("TLS Certificate:\n%s" %
                          pprint.pformat(cert, width=100, compact=True))
            except Exception as e:
                print("TLS Certificate: %s" % repr(e))
    get_btn.on_click(show_ip_info)
    return widgets.VBox([widgets.HBox([ip_field, get_btn]), output])
