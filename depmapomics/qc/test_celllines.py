import re

import numpy as np
import pandas as pd
import pytest
from depmapomics.qc.config import (
    FILE_ATTRIBUTES,
    LINES_TO_DROP,
    LINES_TO_RELEASE,
    IGNORE_FAILED_TO_RELEASE,
    PORTALS,
    LINES_TO_DROP_PER_FILE,
)
from depmapomics.qc.test_compare_to_ref_release import get_both_release_lists_from_taiga
from gsheets.api import Sheets
from taigapy import TaigaClient

tc = TaigaClient()

####### FIXTURES ####
def tsv2csv(df):
    df.to_csv("/tmp/data.tsv", index=False)
    df = pd.read_csv("/tmp/data.tsv", sep="\t")
    return df


@pytest.fixture(scope="module")
def arxspans(request):
    return get_both_release_lists_from_taiga(request.param[0], request.param[1])


PARAMS_unexpected_arxspans = [
    ((x["file"], portal), x["file"], portal, x["omicssource"])
    for x in FILE_ATTRIBUTES
    for portal in PORTALS
]


@pytest.mark.parametrize(
    "arxspans, file, portal, omicssource",
    PARAMS_unexpected_arxspans,
    indirect=["arxspans"],
)
@pytest.mark.bookkeeping
def test_unexpected_arxspans(arxspans, omicssource, portal, file):
    arxspans1, arxspans2 = arxspans

    lines_to_release = LINES_TO_RELEASE[portal]

    dropped_lines = arxspans1 - arxspans2
    added_lines = arxspans2 - arxspans1

    unexpected_added_lines = added_lines - lines_to_release

    lines_to_drop = LINES_TO_DROP[omicssource]
    if file in LINES_TO_DROP_PER_FILE.keys():
        lines_to_drop = lines_to_drop | LINES_TO_DROP_PER_FILE[file]

    unexpected_dropped_lines = dropped_lines - lines_to_drop
    failed_to_drop = lines_to_drop & arxspans2
    if IGNORE_FAILED_TO_RELEASE:
        failed_to_release = set()
    else:
        failed_to_release = lines_to_release - arxspans2

    assert (
        (not unexpected_added_lines)
        & (not unexpected_dropped_lines)
        & (not failed_to_drop)
        & (not failed_to_release)
    ), "\nunexpected added lines: {}\nunexpected dropped lines: {}\nfailed to drop: {}\nfailed to release: {}\n".format(
        unexpected_added_lines,
        unexpected_dropped_lines,
        failed_to_drop,
        failed_to_release,
    )

    # TODO: write a test to make sure data from the same omics source is shared across the files

    # TODO: write a test that checks 'failed_to_release' based on omicssource
