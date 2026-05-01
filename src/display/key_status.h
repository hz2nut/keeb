/*
 * Copyright (c) 2025 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <lvgl.h>
#include <zephyr/kernel.h>

#define CANVAS_SIZE 68
#define CANVAS_COLOR_FORMAT LV_COLOR_FORMAT_L8
#define CANVAS_BUF_SIZE \
	LV_CANVAS_BUF_SIZE(CANVAS_SIZE, CANVAS_SIZE, \
	                   LV_COLOR_FORMAT_GET_BPP(CANVAS_COLOR_FORMAT), \
	                   LV_DRAW_BUF_STRIDE_ALIGN)

struct zmk_widget_key_status {
	sys_snode_t node;
	lv_obj_t *obj;
	uint8_t cbuf_top[CANVAS_BUF_SIZE];
	uint8_t cbuf_mid[CANVAS_BUF_SIZE];
	uint8_t cbuf_btm[CANVAS_BUF_SIZE];
};

int zmk_widget_key_status_init(struct zmk_widget_key_status *widget, lv_obj_t *parent);
lv_obj_t *zmk_widget_key_status_obj(struct zmk_widget_key_status *widget);
