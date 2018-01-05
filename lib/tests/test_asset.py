from __future__ import print_function

import json
import rcAsset
from node import Node

def test_get_connect_to():
    node = Node()
    data_s = json.dumps({
        "networkInterfaces": [
            {
                "accessConfigs": [
                    {
                        "kind": "compute#accessConfig",
                        "name": "external-nat",
                        "natIP": "23.251.137.71",
                        "type": "ONE_TO_ONE_NAT"
                    }
                ],
                "name": "nic0",
                "networkIP": "10.132.0.2",
            }
        ]
    })
    asset = rcAsset.Asset(node)
    ret = asset._parse_connect_to(data_s)
    assert ret == "23.251.137.71"

    data_s = json.dumps({
        "networkInterfaces": [
        ]
    })
    asset = rcAsset.Asset(node)
    ret = asset._parse_connect_to(data_s)
    assert ret is None

    data_s = "{corrupted}"
    asset = rcAsset.Asset(node)
    ret = asset._parse_connect_to(data_s)
    assert ret is None

