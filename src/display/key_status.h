/*
 * Copyright (c) 2025 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <lvgl.h>
#include <zephyr/kernel.h>

struct zmk_widget_key_status {
    sys_snode_t node;
    lv_obj_t *battery_label;
    lv_obj_t *conn_label;
    lv_obj_t *key_label;
    lv_obj_t *layer_label;
};

int zmk_widget_key_status_init(struct zmk_widget_key_status *widget, lv_obj_t *parent);
