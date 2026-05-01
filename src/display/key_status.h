/*
 * Copyright (c) 2025 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <lvgl.h>
#include <zephyr/kernel.h>

#define CANVAS_SIZE 68

struct zmk_widget_key_status {
	sys_snode_t node;
	lv_obj_t *obj;
	lv_color_t cbuf_top[CANVAS_SIZE * CANVAS_SIZE];
	lv_color_t cbuf_mid[CANVAS_SIZE * CANVAS_SIZE];
	lv_color_t cbuf_btm[CANVAS_SIZE * CANVAS_SIZE];
};

int zmk_widget_key_status_init(struct zmk_widget_key_status *widget, lv_obj_t *parent);
lv_obj_t *zmk_widget_key_status_obj(struct zmk_widget_key_status *widget);
