version 1.0

# more information available at https://open-cravat.readthedocs.io/en/latest/2.-Command-line-usage.html
import "merge_vcfs.wdl" as merge_vcfs
import "opencravat.wdl" as openCravat
import "remove_filtered.wdl" as removeFiltered
import "vcf_to_depmap.wdl" as vcf_to_depmap

workflow omics_post_mutect2 {
    input {
        String sample_id
        File vcf
        String annotators="spliceai alfa cscape civic mavedb uniprot loftool fitcons dann dida funseq2 genehancer gwas_catalog pharmgkb provean revel chasmplus oncokb"
        File oncokb_api_key="gs://jkobject/oncokb_key.txt"
        Boolean run_open_cravat=false
    }

    #call merge_vcfs.merge_vcfs as run_merge_vcfs {
    #    input:
    #        sample_id=sample_id,
    #        vcfs=vcfs,
    #        merge_mode='all'
    #}

    call removeFiltered.RemoveFiltered as RemoveFiltered {
        input:
            sample_id=sample_id,
            input_vcf=vcf
    }

    if (run_open_cravat){
        call openCravat.opencravat as open_cravat {
            input:
                sample_id=sample_id,
                vcf=RemoveFiltered.output_vcf
        }
    }

    call vcf_to_depmap.vcf_to_depmap as my_vcf_to_depmap {
        input:
            input_vcf=select_first([open_cravat.oc_main_files,RemoveFiltered.output_vcf]),
            sample_id=sample_id,
    }

    output {
        Array[File] main_output=my_vcf_to_depmap.output_vcf
        File oc_error_files=open_cravat.oc_error_files
        File oc_log_files=open_cravat.oc_log_files
        File oc_sql_files=open_cravat.oc_sql_files
        File somatic_maf=my_vcf_to_depmap.depmap_maf
    }
}