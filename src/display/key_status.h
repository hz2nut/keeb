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
	lv_obj_t *canvas_top;
	lv_obj_t *canvas_mid;
	lv_obj_t *canvas_btm;
	uint8_t cbuf_top[LV_IMG_BUF_SIZE_INDEXED_1BIT(CANVAS_SIZE, CANVAS_SIZE)];
	uint8_t cbuf_mid[LV_IMG_BUF_SIZE_INDEXED_1BIT(CANVAS_SIZE, CANVAS_SIZE)];
	uint8_t cbuf_btm[LV_IMG_BUF_SIZE_INDEXED_1BIT(CANVAS_SIZE, CANVAS_SIZE)];
};

int zmk_widget_key_status_init(struct zmk_widget_key_status *widget, lv_obj_t *parent);
