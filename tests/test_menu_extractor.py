import menu_extractor


def test_extract_categories_builds_expected_hierarchy():
    menu = [
        {
            "level": "1",
            "uniqueID": "L1",
            "jcr:title": "Level 1",
            "seo_url": "l1",
            "aem_url": "/l1",
            "childMenu": [
                {
                    "level": "2",
                    "uniqueID": "L2",
                    "jcr:title": "Level 2",
                    "seo_url": "l2",
                    "aem_url": "/l1/l2",
                    "childMenu": [
                        {
                            "level": "3",
                            "uniqueID": "L3",
                            "jcr:title": "Level 3",
                            "seo_url": "l3",
                            "aem_url": "/l1/l2/l3",
                        }
                    ],
                }
            ],
        }
    ]

    extracted = []
    menu_extractor.extract_categories(menu, level=1, parent_uniqueID=None, data=extracted)

    assert len(extracted) == 3
    assert extracted[0]["UniqueID"] == "L1"
    assert extracted[0]["ParentUniqueID"] is None
    assert extracted[1]["UniqueID"] == "L2"
    assert extracted[1]["ParentUniqueID"] == "L1"
    assert extracted[2]["UniqueID"] == "L3"
    assert extracted[2]["ParentUniqueID"] == "L2"
    assert [row["Level"] for row in extracted] == [1, 2, 3]
