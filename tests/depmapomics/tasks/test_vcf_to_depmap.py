from .utils import run_wdl, assert_output_dirs_match

# The goal of this testing approach is to make sure that the "plumbing" between is correct. This is basically an
# integration test which can detect regressions (changes from previous behavior), but nothing more than that. While
# not an especially robust testing approach, it is much better than nothing.


# Since these pipelines are run on large inputs, it'll be better to keep the data in cloud storage, rather
# than checked into git.
#
# Unfortunately, this means that we lose the ability to keep the test data in sync with the code in the git repository.
# It will be confusing if, in updating a test, we change an input file, causing the test to fail in older versions.
# However, we can avoid this if we
#
# put all GCS paths as constants at the top here with the suffix "GCS_PATH". If we ever need to go clean up the
# bucket, it'll be easier if we can grep out all of the paths out of the code.
SUBSET_VCF_GCS_PATH = "gs://cds-wdl-debug/CDS-ldZUrx.norm.snpeff.clinvar.dbsnp.vep.subset.vcf"
VCS_TO_DEPMAP_EXPECTED_GCS_PATH = (
    "gs://depmapomics-testdata/outputs/230802/test_vcf_to_depmap/expected"
)


def test_vcf_to_depmap(tmpdir):
    run_wdl(
        tmpdir,
        "WGS_pipeline/vcf_to_depmap.wdl",
        {"input_vcf": SUBSET_VCF_GCS_PATH, "sample_id": "test"},
        "test_vcf_to_depmap/latest",
        
    )

    # assert_output_dirs_match(
    #     VCS_TO_DEPMAP_EXPECTED_GCS_PATH, "test_echtvar_cosmic/latest"
    # )
