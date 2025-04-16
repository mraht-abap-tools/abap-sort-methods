"! Automatic creation of Warehouse Products
"! <p>This report is being executed by a job ZIOT_WHSPRD_CREATION and creates warehouse products from ECC products.
"! These products are being sent by the ECC to EWM via IDOCs. After the EWM received these MATMAS-IDOCs a method
"! is being triggered in the enhancement ZIOT_EI_IDOC_INPUT_MATMAS01_E which creates the job if it hasn't been
"! already scheduled or released.</p>
CLASS ziot_cl_whsprd_creation DEFINITION
  PUBLIC
  FINAL
  CREATE PRIVATE .

  PUBLIC SECTION.
    CONSTANTS: mc_job_name  TYPE btcjob   VALUE 'ZIOT_WHSPRD_CREATION',
               mc_rep_name  TYPE btcrep   VALUE 'ZIOT_R_WHSPRD_CREATION',
               mc_fm_name   TYPE progname VALUE 'ZIOT_FM_WHSPRD_CREATION',
               mc_task_name TYPE progname VALUE 'ZIOT_WHSPRD_CREATION'.

    CLASS-METHODS create_job.
    CLASS-METHODS: 
      execute
        IMPORTING
          iv_lgnum    TYPE /scwm/lgnum DEFAULT ziot_constants=>lgnum
          iv_entitled TYPE /scwm/de_entitled DEFAULT ziot_constants=>entitled
        RAISING
          zcx_cp_not_readable
          zcx_plc_not_determinable.
      CLASS-METHODS idoc_input_matmas01_e
        IMPORTING
          iv_lgnum    TYPE /scwm/lgnum DEFAULT ziot_constants=>lgnum
          iv_entitled TYPE /scwm/de_entitled DEFAULT ziot_constants=>entitled
        RAISING
          zcx_cp_not_readable
          zcx_plc_not_determinable.
      CLASS-METHODS idoc_input_matmas02_e.
      CLASS-METHODS idoc_input_matmas03_e
        IMPORTING
          iv_lgnum    TYPE /scwm/lgnum DEFAULT ziot_constants=>lgnum
          iv_entitled TYPE /scwm/de_entitled DEFAULT ziot_constants=>entitled
        RAISING
          zcx_cp_not_readable
          zcx_plc_not_determinable.

  PROTECTED SECTION.
  PRIVATE SECTION.
    CLASS-DATA: mv_lgnum    TYPE /scwm/lgnum VALUE ziot_constants=>lgnum,
                mv_entitled TYPE /scwm/de_entitled VALUE ziot_constants=>entitled,
                mv_msg      TYPE string.

    CLASS-METHODS conv_apo_matkey_to_whsprod
      IMPORTING
        !it_products       TYPE /sapapo/matkey_out_tab
      RETURNING
        VALUE(rt_products) TYPE /scwm/tt_material_lgnum_maint.
    CLASS-METHODS create_whs_products
      IMPORTING
        !it_products TYPE /scwm/tt_material_lgnum_maint.
    CLASS-METHODS dequeue_all
      RAISING
        zcx_cp_not_readable
        zcx_plc_not_determinable.
    CLASS-METHODS 
    det_relevant_products
      RETURNING
        VALUE(rt_products) TYPE /sapapo/matkey_out_tab.
    CLASS-METHODS: lock_products
      IMPORTING
        !it_products TYPE /scwm/tt_material_lgnum_maint.

ENDCLASS.



CLASS ZIOT_CL_WHSPRD_CREATION IMPLEMENTATION.


  METHOD conv_apo_matkey_to_whsprod.

    rt_products = VALUE #( FOR <s_product> IN it_products
                             ( matid    = <s_product>-matguid
                               entitled = mv_entitled ) ).

  ENDMETHOD.


  METHOD create_job.

    TRY.
        DATA(lv_enqueued) = ziot_cl_bs_general=>enqueue( iv_exfunc = mc_task_name
                                                         iv_wait   = abap_false ).

      CATCH cx_root.
    ENDTRY.

    ziot_cl_log=>init( iv_subobject = ziot_constants=>log_subobject_whsprod_creation
                          iv_extnumber = TEXT-001 ).

    DATA(lv_delay) = ziot_cl_bs_config=>get( ziot_constants=>config_delay_create_whsprd ).
    IF lv_delay IS INITIAL.
      lv_delay = 5.
    ENDIF.

    " Time: Current time + n minutes
    DATA(lv_time) = CONV btcstime( sy-uzeit + ( 60 * lv_delay ) ).

    TRY.
        CALL METHOD ziot_cl_job=>create
          EXPORTING
            iv_job_name = mc_job_name
            iv_rep_name = mc_rep_name
            iv_immediat = abap_false
            iv_date     = sy-datum
            iv_time     = lv_time.

      CATCH cx_root.
    ENDTRY.

    TRY.
        ziot_cl_bs_general=>dequeue( iv_exfunc = mc_task_name ).

      CATCH cx_root.
    ENDTRY.

    ziot_cl_log=>get_instance( )->save( ).

  ENDMETHOD.


  METHOD create_whs_products.

    DATA: lt_bapiret TYPE bapirettab.

    CHECK it_products IS NOT INITIAL.

    " Material sperren
    CALL METHOD lock_products
      EXPORTING
        it_products = it_products.

    TRY.
        " Lagerprodukt erzeugen
        CALL FUNCTION '/SCWM/MATERIAL_WHST_MAINT_MULT'
          EXPORTING
            iv_lgnum     = mv_lgnum
            iv_commit    = abap_true
            it_mat_lgnum = it_products
          IMPORTING
            et_bapiret   = lt_bapiret.

      CATCH cx_root.
    ENDTRY.

    ziot_cl_log=>get_instance( )->log_bapiret( lt_bapiret ).

  ENDMETHOD.


  METHOD dequeue_all.

    " Materialien entsperren
    CALL FUNCTION '/SCWM/MATERIAL_WHST_DEQ_ALL'.

    " Laufzeitobjekt entsperren
    ziot_cl_bs_general=>dequeue( iv_exfunc = sy-repid ).

  ENDMETHOD.


  METHOD det_relevant_products.

    DATA: mo_mon_prod_service TYPE REF TO  /scwm/cl_mon_prod.

    CREATE OBJECT mo_mon_prod_service.

    CALL METHOD mo_mon_prod_service->set_lgnum
      EXPORTING
        iv_lgnum = mv_lgnum.

    CALL METHOD mo_mon_prod_service->get_prod_node_data
      EXPORTING
        iv_lgnum            = mv_lgnum
        iv_show_non_wh_only = abap_true
      IMPORTING
        et_data             = DATA(lt_data)
        et_material         = rt_products.

    IF lt_data IS INITIAL.
      CLEAR: rt_products.
    ELSE.
      DATA(lt_r_matid) = VALUE rseloption( FOR <s_data> IN lt_data
                                             ( sign   = 'I'
                                               option = 'EQ'
                                               low    = <s_data>-matid ) ).
      DELETE rt_products WHERE matid NOT IN lt_r_matid.
    ENDIF.

    IF rt_products IS NOT INITIAL.
      MESSAGE s000(ziot_whsprd_creation) INTO mv_msg.
      ziot_cl_log=>get_instance( )->log_message( ).
    ELSE.
      MESSAGE s002(ziot_whsprd_creation) INTO mv_msg.
      ziot_cl_log=>get_instance( )->log_message( ).
    ENDIF.

    LOOP AT rt_products ASSIGNING FIELD-SYMBOL(<ls_product>).
      MESSAGE s001(ziot_whsprd_creation) WITH <ls_product>-matnr <ls_product>-pmtyp <ls_product>-hutyp INTO mv_msg.
      ziot_cl_log=>get_instance( )->log_message( ).
    ENDLOOP.

  ENDMETHOD.


  METHOD execute.

    mv_lgnum    = iv_lgnum.
    mv_entitled = iv_entitled.

    ziot_cl_log=>init( iv_subobject = ziot_constants=>log_subobject_whsprod_creation
                          iv_extnumber = TEXT-000 ).
    ziot_cl_log=>get_instance( )->log_caller( ).

    TRY.
        CALL METHOD ziot_cl_bs_general=>enqueue
          EXPORTING
            iv_exfunc = sy-repid.

        " Anzulegende Lagerprodukte ermitteln und entsprechende Daten vorbereiten
        DATA(lt_products) = det_relevant_products( ).

        DATA(lt_whs_products) = conv_apo_matkey_to_whsprod( lt_products ).

        create_whs_products( lt_whs_products ).

      CATCH cx_root.
    ENDTRY.

    dequeue_all( ).
    ziot_cl_log=>get_instance( )->save( ).

  ENDMETHOD.


  METHOD idoc_input_matmas01_e.

    CALL FUNCTION mc_fm_name
      STARTING NEW TASK mc_task_name.

  ENDMETHOD.


  METHOD idoc_input_matmas02_e.

    CALL FUNCTION mc_fm_name
      STARTING NEW TASK mc_task_name.

  ENDMETHOD.


  METHOD idoc_input_matmas03_e.

    CALL FUNCTION mc_fm_name
      STARTING NEW TASK mc_task_name.

  ENDMETHOD.


  METHOD lock_products.

    CHECK it_products IS NOT INITIAL.

    DATA(lt_matmap) = VALUE /scwm/tt_matid_matnr( FOR <s_product> IN it_products
                                                    ( matid = <s_product>-matid ) ).

    CALL FUNCTION '/SCWM/MATERIAL_WHST_ENQ'
      EXPORTING
        iv_lgnum       = mv_lgnum
        iv_entitled    = mv_entitled
        iv_lock_excl   = abap_true
      CHANGING
        ct_matid_matnr = lt_matmap.

  ENDMETHOD.
  
ENDCLASS.