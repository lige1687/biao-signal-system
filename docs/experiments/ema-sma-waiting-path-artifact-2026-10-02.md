# ema20-sma20-waiting-path-2026-10-02（等待过程的限定描述）

## 一句话结论（大白话）

本次记录EMA刚向上、SMA尚未向上之后，等待SMA跟上时的成功、失败和价格变化。早看与等确认都用同一个结束日期比较；只有实际确认且价格齐全的起点才能相减，这部分结果不能代表全部等待，更不能代表完整账户收益或已获准交易。
资料是已见历史的回顾性重建，不能宣称来自全新验证。

## 性能表（固定终点价格描述）

early_path是全部能计算的早期观察；early_paired_path和waiting_path只用双方价格齐全的共同起点。早期观察从起点后一天收盘开始，等待观察从确认后一天收盘开始，均结束于起点后21个交易日。这些百分比是价格变化，未计算费用、现金或复利账户。

```json
[
  {
    "group": "all",
    "starts": 137,
    "status_counts": {
      "ema_failed": 88,
      "confirmed": 49
    },
    "confirmed": 49,
    "paired_rows": 47,
    "expected_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.9153578915217401,
      "terminal_difference": -1.0345976710702334
    },
    "supported_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 137,
    "confirmed_mature_price_rows": 47,
    "immature_outcomes": 2,
    "asset_count": 4,
    "equal_asset_means": {
      "waiting_cost": 0.8912617321291028,
      "terminal_difference": -0.9896161601531634
    },
    "confirmation_rate": 0.35766423357664234,
    "paired_share": 0.34306569343065696,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 135,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.7174394717577506,
          "lowest_close_decline": 3.758612915963943,
          "highest_close_rise": 4.232103505492255,
          "peak_to_trough_decline": 5.0631105031934345,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.7292834307023479,
          "lowest_close_decline": 3.7966779373792297,
          "highest_close_rise": 4.303825355604607,
          "peak_to_trough_decline": 5.125172555079126,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.8912617321291028,
          "lowest_close_decline": 0.23195226400546443,
          "highest_close_rise": 1.3194048535233318,
          "peak_to_trough_decline": 0.5226793211604952,
          "intervals": 2.524175824175824
        },
        "raw_event_means": {
          "terminal_return": 0.9153578915217401,
          "lowest_close_decline": 0.2592189063013266,
          "highest_close_rise": 1.3872088850037378,
          "peak_to_trough_decline": 0.5603660230983467,
          "intervals": 2.5319148936170213
        }
      },
      "waiting_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.8898968549062558,
          "lowest_close_decline": 2.4997334824166373,
          "highest_close_rise": 4.323831027785609,
          "peak_to_trough_decline": 4.0807910974445525,
          "intervals": 17.475824175824172
        },
        "raw_event_means": {
          "terminal_return": 1.8681930442745815,
          "lowest_close_decline": 2.656795021917858,
          "highest_close_rise": 4.556466328005622,
          "peak_to_trough_decline": 4.409325444174466,
          "intervals": 17.46808510638298
        }
      },
      "early_paired_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.879513015059419,
          "lowest_close_decline": 2.27872215021388,
          "highest_close_rise": 5.436184932994667,
          "peak_to_trough_decline": 4.2513622446947625,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.9027907153448145,
          "lowest_close_decline": 2.4893760715768973,
          "highest_close_rise": 5.735796875008873,
          "peak_to_trough_decline": 4.589421607000176,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "all period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 2
  },
  {
    "group": "510300.SS",
    "starts": 36,
    "status_counts": {
      "ema_failed": 23,
      "confirmed": 13
    },
    "confirmed": 13,
    "paired_rows": 13,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.5795386742594713,
      "terminal_difference": -0.5914590232098823
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 36,
    "confirmed_mature_price_rows": 13,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.5795386742594713,
      "terminal_difference": -0.5914590232098823
    },
    "confirmation_rate": 0.3611111111111111,
    "paired_share": 0.3611111111111111,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 36,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.2791043229220626,
          "lowest_close_decline": 3.204443037714516,
          "highest_close_rise": 2.439539597125649,
          "peak_to_trough_decline": 4.1243954475788325,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.2791043229220626,
          "lowest_close_decline": 3.204443037714516,
          "highest_close_rise": 2.439539597125649,
          "peak_to_trough_decline": 4.1243954475788325,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 13,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.5795386742594713,
          "lowest_close_decline": 0.24866312982350272,
          "highest_close_rise": 1.0093523539542724,
          "peak_to_trough_decline": 0.44162033212600105,
          "intervals": 2.1538461538461537
        },
        "raw_event_means": {
          "terminal_return": 0.5795386742594713,
          "lowest_close_decline": 0.24866312982350272,
          "highest_close_rise": 1.0093523539542724,
          "peak_to_trough_decline": 0.44162033212600105,
          "intervals": 2.1538461538461537
        }
      },
      "waiting_path": {
        "rows": 13,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.7195864720536231,
          "lowest_close_decline": 2.6313237190660357,
          "highest_close_rise": 2.252393355975535,
          "peak_to_trough_decline": 3.3534620499784262,
          "intervals": 17.846153846153847
        },
        "raw_event_means": {
          "terminal_return": 0.7195864720536231,
          "lowest_close_decline": 2.6313237190660357,
          "highest_close_rise": 2.252393355975535,
          "peak_to_trough_decline": 3.3534620499784262,
          "intervals": 17.846153846153847
        }
      },
      "early_paired_path": {
        "rows": 13,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.3110454952635056,
          "lowest_close_decline": 2.349075469117349,
          "highest_close_rise": 3.074977312063001,
          "peak_to_trough_decline": 3.6556516354287183,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.3110454952635056,
          "lowest_close_decline": 2.349075469117349,
          "highest_close_rise": 3.074977312063001,
          "peak_to_trough_decline": 3.6556516354287183,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "all period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS",
    "starts": 31,
    "status_counts": {
      "ema_failed": 23,
      "confirmed": 8
    },
    "confirmed": 8,
    "paired_rows": 7,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.9774691367635262,
      "terminal_difference": -1.0049368331519326
    },
    "supported_assets": [
      "510050.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 31,
    "confirmed_mature_price_rows": 7,
    "immature_outcomes": 1,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.9774691367635262,
      "terminal_difference": -1.0049368331519326
    },
    "confirmation_rate": 0.25806451612903225,
    "paired_share": 0.22580645161290322,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 30,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.0707743646451305,
          "lowest_close_decline": 3.0253217921849807,
          "highest_close_rise": 2.6635598843027095,
          "peak_to_trough_decline": 3.972386093133371,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.0707743646451305,
          "lowest_close_decline": 3.0253217921849807,
          "highest_close_rise": 2.6635598843027095,
          "peak_to_trough_decline": 3.972386093133371,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 7,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.9774691367635262,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.071380245592335,
          "peak_to_trough_decline": 0.20609491308135727,
          "intervals": 2.142857142857143
        },
        "raw_event_means": {
          "terminal_return": 0.9774691367635262,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.071380245592335,
          "peak_to_trough_decline": 0.20609491308135727,
          "intervals": 2.142857142857143
        }
      },
      "waiting_path": {
        "rows": 7,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.6822425435373147,
          "lowest_close_decline": 1.3087009815543655,
          "highest_close_rise": 3.914970253258812,
          "peak_to_trough_decline": 2.226180850233787,
          "intervals": 17.857142857142858
        },
        "raw_event_means": {
          "terminal_return": 2.6822425435373147,
          "lowest_close_decline": 1.3087009815543655,
          "highest_close_rise": 3.914970253258812,
          "peak_to_trough_decline": 2.226180850233787,
          "intervals": 17.857142857142858
        }
      },
      "early_paired_path": {
        "rows": 7,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.687179376689247,
          "lowest_close_decline": 0.6863377641430345,
          "highest_close_rise": 4.930186817461071,
          "peak_to_trough_decline": 2.279041765154249,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 3.687179376689247,
          "lowest_close_decline": 0.6863377641430345,
          "highest_close_rise": 4.930186817461071,
          "peak_to_trough_decline": 2.279041765154249,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "all period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 1
  },
  {
    "group": "510500.SS",
    "starts": 33,
    "status_counts": {
      "ema_failed": 20,
      "confirmed": 13
    },
    "confirmed": 13,
    "paired_rows": 12,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.49168419453240925,
      "terminal_difference": -0.5094887857512042
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 33,
    "confirmed_mature_price_rows": 12,
    "immature_outcomes": 1,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.49168419453240925,
      "terminal_difference": -0.5094887857512042
    },
    "confirmation_rate": 0.3939393939393939,
    "paired_share": 0.36363636363636365,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 32,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.7004607101536129,
          "lowest_close_decline": 3.868298886691626,
          "highest_close_rise": 4.85008740379737,
          "peak_to_trough_decline": 5.102192287486836,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.7004607101536129,
          "lowest_close_decline": 3.868298886691626,
          "highest_close_rise": 4.85008740379737,
          "peak_to_trough_decline": 5.102192287486836,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 12,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.49168419453240925,
          "lowest_close_decline": 0.4121736615061711,
          "highest_close_rise": 1.1252423145256707,
          "peak_to_trough_decline": 0.8305187383681819,
          "intervals": 3.6666666666666665
        },
        "raw_event_means": {
          "terminal_return": 0.49168419453240925,
          "lowest_close_decline": 0.4121736615061711,
          "highest_close_rise": 1.1252423145256707,
          "peak_to_trough_decline": 0.8305187383681819,
          "intervals": 3.6666666666666665
        }
      },
      "waiting_path": {
        "rows": 12,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.8972083070214198,
          "lowest_close_decline": 3.12746254143064,
          "highest_close_rise": 3.1504651709502056,
          "peak_to_trough_decline": 4.364266356215378,
          "intervals": 16.333333333333332
        },
        "raw_event_means": {
          "terminal_return": 0.8972083070214198,
          "lowest_close_decline": 3.12746254143064,
          "highest_close_rise": 3.1504651709502056,
          "peak_to_trough_decline": 4.364266356215378,
          "intervals": 16.333333333333332
        }
      },
      "early_paired_path": {
        "rows": 12,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.406697092772624,
          "lowest_close_decline": 3.177933532446561,
          "highest_close_rise": 3.6657312301494893,
          "peak_to_trough_decline": 4.6117605868620215,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.406697092772624,
          "lowest_close_decline": 3.177933532446561,
          "highest_close_rise": 3.6657312301494893,
          "peak_to_trough_decline": 4.6117605868620215,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "all period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 1
  },
  {
    "group": "588000.SS",
    "starts": 37,
    "status_counts": {
      "ema_failed": 22,
      "confirmed": 15
    },
    "confirmed": 15,
    "paired_rows": 15,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.5163549229610045,
      "terminal_difference": -1.8525799984996343
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 37,
    "confirmed_mature_price_rows": 15,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.5163549229610045,
      "terminal_difference": -1.8525799984996343
    },
    "confirmation_rate": 0.40540540540540543,
    "paired_share": 0.40540540540540543,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 37,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.5191758644445823,
          "lowest_close_decline": 4.93638794726465,
          "highest_close_rise": 6.975227136743287,
          "peak_to_trough_decline": 7.053468184574697,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.5191758644445823,
          "lowest_close_decline": 4.93638794726465,
          "highest_close_rise": 6.975227136743287,
          "peak_to_trough_decline": 7.053468184574697,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 15,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.5163549229610045,
          "lowest_close_decline": 0.26697226469218394,
          "highest_close_rise": 2.0716445000210495,
          "peak_to_trough_decline": 0.6124833010664407,
          "intervals": 2.1333333333333333
        },
        "raw_event_means": {
          "terminal_return": 1.5163549229610045,
          "lowest_close_decline": 0.26697226469218394,
          "highest_close_rise": 2.0716445000210495,
          "peak_to_trough_decline": 0.6124833010664407,
          "intervals": 2.1333333333333333
        }
      },
      "waiting_path": {
        "rows": 15,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.2605500970126653,
          "lowest_close_decline": 2.931446687615508,
          "highest_close_rise": 7.977495330957881,
          "peak_to_trough_decline": 6.379255133350619,
          "intervals": 17.866666666666667
        },
        "raw_event_means": {
          "terminal_return": 3.2605500970126653,
          "lowest_close_decline": 2.931446687615508,
          "highest_close_rise": 7.977495330957881,
          "peak_to_trough_decline": 6.379255133350619,
          "intervals": 17.866666666666667
        }
      },
      "early_paired_path": {
        "rows": 15,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 5.1131300955123,
          "lowest_close_decline": 2.9015418351485764,
          "highest_close_rise": 10.073844372305107,
          "peak_to_trough_decline": 6.458994991334062,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 5.1131300955123,
          "lowest_close_decline": 2.9015418351485764,
          "highest_close_rise": 10.073844372305107,
          "peak_to_trough_decline": 6.458994991334062,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "all period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "2022-2024",
    "starts": 92,
    "status_counts": {
      "ema_failed": 62,
      "confirmed": 30
    },
    "confirmed": 30,
    "paired_rows": 29,
    "expected_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.9812658511869732,
      "terminal_difference": -1.113238006126352
    },
    "supported_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 87,
    "confirmed_mature_price_rows": 29,
    "immature_outcomes": 0,
    "asset_count": 4,
    "equal_asset_means": {
      "waiting_cost": 0.9253893201327739,
      "terminal_difference": -1.0259572846100125
    },
    "confirmation_rate": 0.32608695652173914,
    "paired_share": 0.31521739130434784,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 87,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.39498922734966424,
          "lowest_close_decline": 4.423903461755178,
          "highest_close_rise": 3.7065863746518226,
          "peak_to_trough_decline": 5.736789378662937,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.3523824979648278,
          "lowest_close_decline": 4.43217896586792,
          "highest_close_rise": 3.788829940944318,
          "peak_to_trough_decline": 5.778198460864012,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 29,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.9253893201327739,
          "lowest_close_decline": 0.24454406281591004,
          "highest_close_rise": 1.4425322287904043,
          "peak_to_trough_decline": 0.5859230264154804,
          "intervals": 2.568253968253968
        },
        "raw_event_means": {
          "terminal_return": 0.9812658511869732,
          "lowest_close_decline": 0.2841816055446315,
          "highest_close_rise": 1.5718679484772695,
          "peak_to_trough_decline": 0.6798580364015608,
          "intervals": 2.7586206896551726
        }
      },
      "waiting_path": {
        "rows": 29,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.681080135666086,
          "lowest_close_decline": 3.002157273086283,
          "highest_close_rise": 4.367210854507585,
          "peak_to_trough_decline": 4.4356987312234715,
          "intervals": 17.43174603174603
        },
        "raw_event_means": {
          "terminal_return": 1.34758569798844,
          "lowest_close_decline": 3.093638329011283,
          "highest_close_rise": 4.651483749122105,
          "peak_to_trough_decline": 4.975278154099609,
          "intervals": 17.24137931034483
        }
      },
      "early_paired_path": {
        "rows": 29,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.707037420276098,
          "lowest_close_decline": 2.6092608123110708,
          "highest_close_rise": 5.589094269719842,
          "peak_to_trough_decline": 4.711505697530214,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.4608237041147922,
          "lowest_close_decline": 2.828371916041922,
          "highest_close_rise": 5.992028355005254,
          "peak_to_trough_decline": 5.2596933435242414,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 5,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "2025",
    "starts": 31,
    "status_counts": {
      "ema_failed": 19,
      "confirmed": 12
    },
    "confirmed": 12,
    "paired_rows": 11,
    "expected_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.27377096060117084,
      "terminal_difference": -0.2917525604279082
    },
    "supported_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 23,
    "confirmed_mature_price_rows": 11,
    "immature_outcomes": 0,
    "asset_count": 4,
    "equal_asset_means": {
      "waiting_cost": 0.21679303645204617,
      "terminal_difference": -0.23397492550580126
    },
    "confirmation_rate": 0.3870967741935484,
    "paired_share": 0.3548387096774194,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 23,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.7285882321699186,
          "lowest_close_decline": 1.718530801941362,
          "highest_close_rise": 4.387559590973649,
          "peak_to_trough_decline": 3.2258606854080702,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.830473604119237,
          "lowest_close_decline": 1.9236891985508116,
          "highest_close_rise": 4.719128991482853,
          "peak_to_trough_decline": 3.528040925684077,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 11,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.21679303645204617,
          "lowest_close_decline": 0.25985883770290924,
          "highest_close_rise": 0.537280685366577,
          "peak_to_trough_decline": 0.332856845022165,
          "intervals": 1.5
        },
        "raw_event_means": {
          "terminal_return": 0.27377096060117084,
          "lowest_close_decline": 0.21868866224441075,
          "highest_close_rise": 0.5328808997026734,
          "peak_to_trough_decline": 0.2775318620439155,
          "intervals": 1.4545454545454546
        }
      },
      "waiting_path": {
        "rows": 11,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.332665004845232,
          "lowest_close_decline": 2.095168922616655,
          "highest_close_rise": 2.7829046188196322,
          "peak_to_trough_decline": 3.5396850907929642,
          "intervals": 18.5
        },
        "raw_event_means": {
          "terminal_return": 1.4298770314456233,
          "lowest_close_decline": 2.0506848598957528,
          "highest_close_rise": 2.8714531750573284,
          "peak_to_trough_decline": 3.4946762971139282,
          "intervals": 18.545454545454547
        }
      },
      "early_paired_path": {
        "rows": 11,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.566639930351033,
          "lowest_close_decline": 2.0046943417825966,
          "highest_close_rise": 3.0149262027825774,
          "peak_to_trough_decline": 3.5396850907929642,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.7216295918735318,
          "lowest_close_decline": 1.9186270417175886,
          "highest_close_rise": 3.1626480282252474,
          "peak_to_trough_decline": 3.4946762971139282,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 8,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "2026H1",
    "starts": 14,
    "status_counts": {
      "ema_failed": 7,
      "confirmed": 7
    },
    "confirmed": 7,
    "paired_rows": 5,
    "expected_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 2.372089961475509,
      "terminal_difference": -2.6773782471159135
    },
    "supported_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 12,
    "confirmed_mature_price_rows": 5,
    "immature_outcomes": 2,
    "asset_count": 4,
    "equal_asset_means": {
      "waiting_cost": 2.6710340800619115,
      "terminal_difference": -3.031937216612869
    },
    "confirmation_rate": 0.5,
    "paired_share": 0.35714285714285715,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 12,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.150972467397706,
          "lowest_close_decline": 3.5899031180339533,
          "highest_close_rise": 6.824414822761822,
          "peak_to_trough_decline": 4.811637386993951,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.3557880348842906,
          "lowest_close_decline": 3.9761802054542774,
          "highest_close_rise": 5.300275736591342,
          "peak_to_trough_decline": 4.970639462117045,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 5,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.6710340800619115,
          "lowest_close_decline": 0.039473684210526314,
          "highest_close_rise": 2.827015113707056,
          "peak_to_trough_decline": 0.4997289589659223,
          "intervals": 4.375
        },
        "raw_event_means": {
          "terminal_return": 2.372089961475509,
          "lowest_close_decline": 0.06315789473684211,
          "highest_close_rise": 2.567823814500203,
          "peak_to_trough_decline": 0.46956245409973274,
          "intervals": 4.0
        }
      },
      "waiting_path": {
        "rows": 5,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 8.256713456872685,
          "lowest_close_decline": 0.8467577340918304,
          "highest_close_rise": 9.338464277691994,
          "peak_to_trough_decline": 2.445521910272207,
          "intervals": 15.625
        },
        "raw_event_means": {
          "terminal_return": 6.775063680446301,
          "lowest_close_decline": 1.3215455748130631,
          "highest_close_rise": 8.058682296265957,
          "peak_to_trough_decline": 2.693675190493704,
          "intervals": 16.0
        }
      },
      "early_paired_path": {
        "rows": 5,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 11.288650673485554,
          "lowest_close_decline": 0.8421052631578947,
          "highest_close_rise": 12.40809468967883,
          "peak_to_trough_decline": 2.4725818052089577,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 9.452441927562216,
          "lowest_close_decline": 1.3473684210526315,
          "highest_close_rise": 10.788243030833177,
          "peak_to_trough_decline": 2.7369710223925052,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 2
  },
  {
    "group": "510300.SS|2022-2024",
    "starts": 24,
    "status_counts": {
      "ema_failed": 17,
      "confirmed": 7
    },
    "confirmed": 7,
    "paired_rows": 7,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.4185233786967108,
      "terminal_difference": -0.4045723561257018
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 23,
    "confirmed_mature_price_rows": 7,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.4185233786967108,
      "terminal_difference": -0.4045723561257018
    },
    "confirmation_rate": 0.2916666666666667,
    "paired_share": 0.2916666666666667,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 23,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -1.1622277317448841,
          "lowest_close_decline": 3.8807699048303608,
          "highest_close_rise": 2.0665220252886334,
          "peak_to_trough_decline": 4.743680554845837,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -1.1622277317448841,
          "lowest_close_decline": 3.8807699048303608,
          "highest_close_rise": 2.0665220252886334,
          "peak_to_trough_decline": 4.743680554845837,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 7,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.4185233786967108,
          "lowest_close_decline": 0.38695923839371094,
          "highest_close_rise": 1.0972039384411694,
          "peak_to_trough_decline": 0.6726532320888147,
          "intervals": 2.4285714285714284
        },
        "raw_event_means": {
          "terminal_return": 0.4185233786967108,
          "lowest_close_decline": 0.38695923839371094,
          "highest_close_rise": 1.0972039384411694,
          "peak_to_trough_decline": 0.6726532320888147,
          "intervals": 2.4285714285714284
        }
      },
      "waiting_path": {
        "rows": 7,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.5162065934552764,
          "lowest_close_decline": 3.019779396382392,
          "highest_close_rise": 1.9550324333522102,
          "peak_to_trough_decline": 3.5745934427068504,
          "intervals": 17.571428571428573
        },
        "raw_event_means": {
          "terminal_return": 0.5162065934552764,
          "lowest_close_decline": 3.019779396382392,
          "highest_close_rise": 1.9550324333522102,
          "peak_to_trough_decline": 3.5745934427068504,
          "intervals": 17.571428571428573
        }
      },
      "early_paired_path": {
        "rows": 7,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.9207789495809785,
          "lowest_close_decline": 2.61984942322248,
          "highest_close_rise": 2.7560348820198155,
          "peak_to_trough_decline": 4.104877078615391,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.9207789495809785,
          "lowest_close_decline": 2.61984942322248,
          "highest_close_rise": 2.7560348820198155,
          "peak_to_trough_decline": 4.104877078615391,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 1,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510300.SS|2025",
    "starts": 8,
    "status_counts": {
      "ema_failed": 4,
      "confirmed": 4
    },
    "confirmed": 4,
    "paired_rows": 4,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.5629280350590884,
      "terminal_difference": -0.584669017648093
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 6,
    "confirmed_mature_price_rows": 4,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.5629280350590884,
      "terminal_difference": -0.584669017648093
    },
    "confirmation_rate": 0.5,
    "paired_share": 0.5,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 6,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.7446276077243084,
          "lowest_close_decline": 1.1599916446226786,
          "highest_close_rise": 3.148949200227586,
          "peak_to_trough_decline": 2.6620079681329627,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.7446276077243084,
          "lowest_close_decline": 1.1599916446226786,
          "highest_close_rise": 3.148949200227586,
          "peak_to_trough_decline": 2.6620079681329627,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 4,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.5629280350590884,
          "lowest_close_decline": 0.05202913631633715,
          "highest_close_rise": 0.5947589492429437,
          "peak_to_trough_decline": 0.08367470593659032,
          "intervals": 1.5
        },
        "raw_event_means": {
          "terminal_return": 0.5629280350590884,
          "lowest_close_decline": 0.05202913631633715,
          "highest_close_rise": 0.5947589492429437,
          "peak_to_trough_decline": 0.08367470593659032,
          "intervals": 1.5
        }
      },
      "waiting_path": {
        "rows": 4,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.0110622082571576,
          "lowest_close_decline": 1.6568396744464318,
          "highest_close_rise": 2.4291944632732196,
          "peak_to_trough_decline": 2.8000689820030527,
          "intervals": 18.5
        },
        "raw_event_means": {
          "terminal_return": 1.0110622082571576,
          "lowest_close_decline": 1.6568396744464318,
          "highest_close_rise": 2.4291944632732196,
          "peak_to_trough_decline": 2.8000689820030527,
          "intervals": 18.5
        }
      },
      "early_paired_path": {
        "rows": 4,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.5957312259052507,
          "lowest_close_decline": 1.3655482576762545,
          "highest_close_rise": 3.016197022944792,
          "peak_to_trough_decline": 2.8000689820030527,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.5957312259052507,
          "lowest_close_decline": 1.3655482576762545,
          "highest_close_rise": 3.016197022944792,
          "peak_to_trough_decline": 2.8000689820030527,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510300.SS|2026H1",
    "starts": 4,
    "status_counts": {
      "ema_failed": 2,
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 2,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.1763134871298981,
      "terminal_difference": -1.2591423691280923
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 4,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.1763134871298981,
      "terminal_difference": -1.2591423691280923
    },
    "confirmation_rate": 0.5,
    "paired_share": 0.5,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 4,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.6680910175973427,
          "lowest_close_decline": 2.7025726856272985,
          "highest_close_rise": 2.623567816655942,
          "peak_to_trough_decline": 3.370948156089663,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.6680910175973427,
          "lowest_close_decline": 2.7025726856272985,
          "highest_close_rise": 2.623567816655942,
          "peak_to_trough_decline": 3.370948156089663,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.1763134871298981,
          "lowest_close_decline": 0.15789473684210525,
          "highest_close_rise": 1.531058617672791,
          "peak_to_trough_decline": 0.34889643463497455,
          "intervals": 2.5
        },
        "raw_event_means": {
          "terminal_return": 1.1763134871298981,
          "lowest_close_decline": 0.15789473684210525,
          "highest_close_rise": 1.531058617672791,
          "peak_to_trough_decline": 0.34889643463497455,
          "intervals": 2.5
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.8484645747407664,
          "lowest_close_decline": 3.2206969376979937,
          "highest_close_rise": 2.9395543705618037,
          "peak_to_trough_decline": 3.6862883113796903,
          "intervals": 17.5
        },
        "raw_event_means": {
          "terminal_return": 0.8484645747407664,
          "lowest_close_decline": 3.2206969376979937,
          "highest_close_rise": 2.9395543705618037,
          "peak_to_trough_decline": 3.6862883113796903,
          "intervals": 17.5
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.1076069438688587,
          "lowest_close_decline": 3.3684210526315788,
          "highest_close_rise": 4.308836395450569,
          "peak_to_trough_decline": 3.794527891126694,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.1076069438688587,
          "lowest_close_decline": 3.3684210526315788,
          "highest_close_rise": 4.308836395450569,
          "peak_to_trough_decline": 3.794527891126694,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS|2022-2024",
    "starts": 20,
    "status_counts": {
      "ema_failed": 17,
      "confirmed": 3
    },
    "confirmed": 3,
    "paired_rows": 3,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.9829958167376999,
      "terminal_difference": -1.0180361402772504
    },
    "supported_assets": [
      "510050.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 17,
    "confirmed_mature_price_rows": 3,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.9829958167376999,
      "terminal_difference": -1.0180361402772504
    },
    "confirmation_rate": 0.15,
    "paired_share": 0.15,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 17,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.9002086191722227,
          "lowest_close_decline": 4.175208035514505,
          "highest_close_rise": 2.1193791198200915,
          "peak_to_trough_decline": 4.798376014859854,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.9002086191722227,
          "lowest_close_decline": 4.175208035514505,
          "highest_close_rise": 2.1193791198200915,
          "peak_to_trough_decline": 4.798376014859854,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 3,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.9829958167376999,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.1123954026590248,
          "peak_to_trough_decline": 0.12698412698412698,
          "intervals": 1.6666666666666667
        },
        "raw_event_means": {
          "terminal_return": 0.9829958167376999,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.1123954026590248,
          "peak_to_trough_decline": 0.12698412698412698,
          "intervals": 1.6666666666666667
        }
      },
      "waiting_path": {
        "rows": 3,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.7358684392195065,
          "lowest_close_decline": 2.5626918990233296,
          "highest_close_rise": 4.419009308764509,
          "peak_to_trough_decline": 2.5626918990233296,
          "intervals": 18.333333333333332
        },
        "raw_event_means": {
          "terminal_return": 3.7358684392195065,
          "lowest_close_decline": 2.5626918990233296,
          "highest_close_rise": 4.419009308764509,
          "peak_to_trough_decline": 2.5626918990233296,
          "intervals": 18.333333333333332
        }
      },
      "early_paired_path": {
        "rows": 3,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.753904579496756,
          "lowest_close_decline": 1.601454783000414,
          "highest_close_rise": 5.443652302202264,
          "peak_to_trough_decline": 2.6860340338377404,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 4.753904579496756,
          "lowest_close_decline": 1.601454783000414,
          "highest_close_rise": 5.443652302202264,
          "peak_to_trough_decline": 2.6860340338377404,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 3,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS|2025",
    "starts": 6,
    "status_counts": {
      "ema_failed": 3,
      "confirmed": 3
    },
    "confirmed": 3,
    "paired_rows": 2,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.9177238099334921,
      "terminal_difference": -0.9393464352369579
    },
    "supported_assets": [
      "510050.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 4,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.9177238099334921,
      "terminal_difference": -0.9393464352369579
    },
    "confirmation_rate": 0.5,
    "paired_share": 0.3333333333333333,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 4,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.760905882921916,
          "lowest_close_decline": 0.47451370892919986,
          "highest_close_rise": 3.6779414775675368,
          "peak_to_trough_decline": 1.700461935103458,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.760905882921916,
          "lowest_close_decline": 0.47451370892919986,
          "highest_close_rise": 3.6779414775675368,
          "peak_to_trough_decline": 1.700461935103458,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.9177238099334921,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 0.9177238099334921,
          "peak_to_trough_decline": 0.0,
          "intervals": 1.0
        },
        "raw_event_means": {
          "terminal_return": 0.9177238099334921,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 0.9177238099334921,
          "peak_to_trough_decline": 0.0,
          "intervals": 1.0
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.6665584937383329,
          "lowest_close_decline": 0.6532485875706214,
          "highest_close_rise": 2.8153549926442407,
          "peak_to_trough_decline": 1.8957051015926307,
          "intervals": 19.0
        },
        "raw_event_means": {
          "terminal_return": 1.6665584937383329,
          "lowest_close_decline": 0.6532485875706214,
          "highest_close_rise": 2.8153549926442407,
          "peak_to_trough_decline": 1.8957051015926307,
          "intervals": 19.0
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.6059049289752907,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 3.759328583314361,
          "peak_to_trough_decline": 1.8957051015926307,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.6059049289752907,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 3.759328583314361,
          "peak_to_trough_decline": 1.8957051015926307,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS|2026H1",
    "starts": 5,
    "status_counts": {
      "ema_failed": 3,
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 1,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.1440107671601616,
      "terminal_difference": -1.1698899195776238
    },
    "supported_assets": [
      "510050.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 4,
    "confirmed_mature_price_rows": 1,
    "immature_outcomes": 1,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.1440107671601616,
      "terminal_difference": -1.1698899195776238
    },
    "confirmation_rate": 0.4,
    "paired_share": 0.2,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 4,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.341177459745432,
          "lowest_close_decline": 1.9327523634165937,
          "highest_close_rise": 2.893895243723202,
          "peak_to_trough_decline": 2.842221630071095,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.341177459745432,
          "lowest_close_decline": 1.9327523634165937,
          "highest_close_rise": 2.893895243723202,
          "peak_to_trough_decline": 2.842221630071095,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.1440107671601616,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.4131897711978465,
          "peak_to_trough_decline": 1.06171201061712,
          "intervals": 6.0
        },
        "raw_event_means": {
          "terminal_return": 1.1440107671601616,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.4131897711978465,
          "peak_to_trough_decline": 1.06171201061712,
          "intervals": 6.0
        }
      },
      "waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.2621423819028608,
          "lowest_close_decline": 0.16633399866932802,
          "highest_close_rise": 3.8922155688622753,
          "peak_to_trough_decline": 1.569004162664105,
          "intervals": 14.0
        },
        "raw_event_means": {
          "terminal_return": 2.2621423819028608,
          "lowest_close_decline": 0.16633399866932802,
          "highest_close_rise": 3.8922155688622753,
          "peak_to_trough_decline": 1.569004162664105,
          "intervals": 14.0
        }
      },
      "early_paired_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.4320323014804845,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 5.0807537012113055,
          "peak_to_trough_decline": 1.569004162664105,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 3.4320323014804845,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 5.0807537012113055,
          "peak_to_trough_decline": 1.569004162664105,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 1
  },
  {
    "group": "510500.SS|2022-2024",
    "starts": 25,
    "status_counts": {
      "ema_failed": 16,
      "confirmed": 9
    },
    "confirmed": 9,
    "paired_rows": 9,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.42232226763469577,
      "terminal_difference": -0.4144191564184372
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 25,
    "confirmed_mature_price_rows": 9,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.42232226763469577,
      "terminal_difference": -0.4144191564184372
    },
    "confirmation_rate": 0.36,
    "paired_share": 0.36,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 25,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.2543197732380628,
          "lowest_close_decline": 4.430445222931815,
          "highest_close_rise": 3.9929924888690347,
          "peak_to_trough_decline": 5.704666764094716,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.2543197732380628,
          "lowest_close_decline": 4.430445222931815,
          "highest_close_rise": 3.9929924888690347,
          "peak_to_trough_decline": 5.704666764094716,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 9,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.42232226763469577,
          "lowest_close_decline": 0.37961823666095473,
          "highest_close_rise": 1.0387390118386672,
          "peak_to_trough_decline": 0.8141894158186209,
          "intervals": 3.7777777777777777
        },
        "raw_event_means": {
          "terminal_return": 0.42232226763469577,
          "lowest_close_decline": 0.37961823666095473,
          "highest_close_rise": 1.0387390118386672,
          "peak_to_trough_decline": 0.8141894158186209,
          "intervals": 3.7777777777777777
        }
      },
      "waiting_path": {
        "rows": 9,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.463521330076293,
          "lowest_close_decline": 3.372597899813657,
          "highest_close_rise": 2.997242994354098,
          "peak_to_trough_decline": 4.482259158766354,
          "intervals": 16.22222222222222
        },
        "raw_event_means": {
          "terminal_return": 0.463521330076293,
          "lowest_close_decline": 3.372597899813657,
          "highest_close_rise": 2.997242994354098,
          "peak_to_trough_decline": 4.482259158766354,
          "intervals": 16.22222222222222
        }
      },
      "early_paired_path": {
        "rows": 9,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.8779404864947301,
          "lowest_close_decline": 3.2779151765567622,
          "highest_close_rise": 3.421277732166013,
          "peak_to_trough_decline": 4.812251466295212,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.8779404864947301,
          "lowest_close_decline": 3.2779151765567622,
          "highest_close_rise": 3.421277732166013,
          "peak_to_trough_decline": 4.812251466295212,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510500.SS|2025",
    "starts": 6,
    "status_counts": {
      "ema_failed": 4,
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 2,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": -0.76475990406273,
      "terminal_difference": 0.7562564762262394
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 4,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": -0.76475990406273,
      "terminal_difference": 0.7562564762262394
    },
    "confirmation_rate": 0.3333333333333333,
    "paired_share": 0.3333333333333333,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 4,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.81797424511842,
          "lowest_close_decline": 2.3539427649412685,
          "highest_close_rise": 4.315124696485054,
          "peak_to_trough_decline": 3.699541960808116,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.81797424511842,
          "lowest_close_decline": 2.3539427649412685,
          "highest_close_rise": 4.315124696485054,
          "peak_to_trough_decline": 3.699541960808116,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.76475990406273,
          "lowest_close_decline": 0.76475990406273,
          "highest_close_rise": 0.2627134669789683,
          "peak_to_trough_decline": 1.0251063637194997,
          "intervals": 2.5
        },
        "raw_event_means": {
          "terminal_return": -0.76475990406273,
          "lowest_close_decline": 0.76475990406273,
          "highest_close_rise": 0.2627134669789683,
          "peak_to_trough_decline": 1.0251063637194997,
          "intervals": 2.5
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.3921635732402453,
          "lowest_close_decline": 3.5880846994223834,
          "highest_close_rise": 1.4227099708339512,
          "peak_to_trough_decline": 4.939145701672771,
          "intervals": 17.5
        },
        "raw_event_means": {
          "terminal_return": -0.3921635732402453,
          "lowest_close_decline": 3.5880846994223834,
          "highest_close_rise": 1.4227099708339512,
          "peak_to_trough_decline": 4.939145701672771,
          "intervals": 17.5
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -1.1484200494664847,
          "lowest_close_decline": 4.3169829001739375,
          "highest_close_rise": 0.6468545625436483,
          "peak_to_trough_decline": 4.939145701672771,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -1.1484200494664847,
          "lowest_close_decline": 4.3169829001739375,
          "highest_close_rise": 0.6468545625436483,
          "peak_to_trough_decline": 4.939145701672771,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510500.SS|2026H1",
    "starts": 2,
    "status_counts": {
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 1,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 3.6288297338021094,
      "terminal_difference": -3.8966059737009937
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 1,
    "confirmed_mature_price_rows": 1,
    "immature_outcomes": 1,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 3.6288297338021094,
      "terminal_difference": -3.8966059737009937
    },
    "confirmation_rate": 1.0,
    "paired_share": 0.5,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 11.275740833751884,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 11.903566047212456,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 11.275740833751884,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 11.903566047212456,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.6288297338021094,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 3.6288297338021094,
          "peak_to_trough_decline": 0.5883073906115945,
          "intervals": 5.0
        },
        "raw_event_means": {
          "terminal_return": 3.6288297338021094,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 3.6288297338021094,
          "peak_to_trough_decline": 0.5883073906115945,
          "intervals": 5.0
        }
      },
      "waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 7.379134860050891,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 7.9849751605476795,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 15.0
        },
        "raw_event_means": {
          "terminal_return": 7.379134860050891,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 7.9849751605476795,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 15.0
        }
      },
      "early_paired_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 11.275740833751884,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 11.903566047212456,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 11.275740833751884,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 11.903566047212456,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 1
  },
  {
    "group": "588000.SS|2022-2024",
    "starts": 23,
    "status_counts": {
      "ema_failed": 12,
      "confirmed": 11
    },
    "confirmed": 11,
    "paired_rows": 10,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.8777158174619892,
      "terminal_difference": -2.26680148561866
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 22,
    "confirmed_mature_price_rows": 10,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.8777158174619892,
      "terminal_difference": -2.26680148561866
    },
    "confirmation_rate": 0.4782608695652174,
    "paired_share": 0.43478260869565216,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 22,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.22815966828038692,
          "lowest_close_decline": 5.2091906837440325,
          "highest_close_rise": 6.647451864629531,
          "peak_to_trough_decline": 7.700434180851343,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.22815966828038692,
          "lowest_close_decline": 5.2091906837440325,
          "highest_close_rise": 6.647451864629531,
          "peak_to_trough_decline": 7.700434180851343,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 10,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.8777158174619892,
          "lowest_close_decline": 0.21159877620897447,
          "highest_close_rise": 2.5217905622227557,
          "peak_to_trough_decline": 0.7298653307703594,
          "intervals": 2.4
        },
        "raw_event_means": {
          "terminal_return": 1.8777158174619892,
          "lowest_close_decline": 0.21159877620897447,
          "highest_close_rise": 2.5217905622227557,
          "peak_to_trough_decline": 0.7298653307703594,
          "intervals": 2.4
        }
      },
      "waiting_path": {
        "rows": 10,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.008724179913268,
          "lowest_close_decline": 3.0535598971257527,
          "highest_close_rise": 8.09755868155952,
          "peak_to_trough_decline": 7.123250424397351,
          "intervals": 17.6
        },
        "raw_event_means": {
          "terminal_return": 2.008724179913268,
          "lowest_close_decline": 3.0535598971257527,
          "highest_close_rise": 8.09755868155952,
          "peak_to_trough_decline": 7.123250424397351,
          "intervals": 17.6
        }
      },
      "early_paired_path": {
        "rows": 10,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.275525665531928,
          "lowest_close_decline": 2.9378238664646275,
          "highest_close_rise": 10.735412162491274,
          "peak_to_trough_decline": 7.2428602113725145,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 4.275525665531928,
          "lowest_close_decline": 2.9378238664646275,
          "highest_close_rise": 10.735412162491274,
          "peak_to_trough_decline": 7.2428602113725145,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 1,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "588000.SS|2025",
    "starts": 11,
    "status_counts": {
      "ema_failed": 8,
      "confirmed": 3
    },
    "confirmed": 3,
    "paired_rows": 3,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.15128020487833418,
      "terminal_difference": -0.16814072536439348
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 9,
    "confirmed_mature_price_rows": 3,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.15128020487833418,
      "terminal_difference": -0.16814072536439348
    },
    "confirmation_rate": 0.2727272727272727,
    "paired_share": 0.2727272727272727,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 9,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.59084519291503,
          "lowest_close_decline": 2.885675089272301,
          "highest_close_rise": 6.408222989614419,
          "peak_to_trough_decline": 4.841430877587744,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 3.59084519291503,
          "lowest_close_decline": 2.885675089272301,
          "highest_close_rise": 6.408222989614419,
          "peak_to_trough_decline": 4.841430877587744,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.15128020487833418,
          "lowest_close_decline": 0.22264631043256997,
          "highest_close_rise": 0.37392651531090415,
          "peak_to_trough_decline": 0.22264631043256997,
          "intervals": 1.0
        },
        "raw_event_means": {
          "terminal_return": 0.15128020487833418,
          "lowest_close_decline": 0.22264631043256997,
          "highest_close_rise": 0.37392651531090415,
          "peak_to_trough_decline": 0.22264631043256997,
          "intervals": 1.0
        }
      },
      "waiting_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.045202890625683,
          "lowest_close_decline": 2.482502729027183,
          "highest_close_rise": 4.4643590485271165,
          "peak_to_trough_decline": 4.523820577903402,
          "intervals": 19.0
        },
        "raw_event_means": {
          "terminal_return": 3.045202890625683,
          "lowest_close_decline": 2.482502729027183,
          "highest_close_rise": 4.4643590485271165,
          "peak_to_trough_decline": 4.523820577903402,
          "intervals": 19.0
        }
      },
      "early_paired_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.2133436159900763,
          "lowest_close_decline": 2.336246209280195,
          "highest_close_rise": 4.637324642327509,
          "peak_to_trough_decline": 4.523820577903402,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 3.2133436159900763,
          "lowest_close_decline": 2.336246209280195,
          "highest_close_rise": 4.637324642327509,
          "peak_to_trough_decline": 4.523820577903402,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "588000.SS|2026H1",
    "starts": 3,
    "status_counts": {
      "ema_failed": 2,
      "confirmed": 1
    },
    "confirmed": 1,
    "paired_rows": 1,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 4.734982332155477,
      "terminal_difference": -5.802110604044767
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 3,
    "confirmed_mature_price_rows": 1,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 4.734982332155477,
      "terminal_difference": -5.802110604044767
    },
    "confirmation_rate": 0.3333333333333333,
    "paired_share": 0.3333333333333333,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.3188805584961673,
          "lowest_close_decline": 9.724287423091921,
          "highest_close_rise": 9.87663018345569,
          "peak_to_trough_decline": 10.880807319473233,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.3188805584961673,
          "lowest_close_decline": 9.724287423091921,
          "highest_close_rise": 9.87663018345569,
          "peak_to_trough_decline": 10.880807319473233,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 1,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.734982332155477,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 4.734982332155477,
          "peak_to_trough_decline": 0.0,
          "intervals": 4.0
        },
        "raw_event_means": {
          "terminal_return": 4.734982332155477,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 4.734982332155477,
          "peak_to_trough_decline": 0.0,
          "intervals": 4.0
        }
      },
      "waiting_path": {
        "rows": 1,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 22.53711201079622,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 22.53711201079622,
          "peak_to_trough_decline": 2.3742227247032224,
          "intervals": 16.0
        },
        "raw_event_means": {
          "terminal_return": 22.53711201079622,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 22.53711201079622,
          "peak_to_trough_decline": 2.3742227247032224,
          "intervals": 16.0
        }
      },
      "early_paired_path": {
        "rows": 1,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 28.33922261484099,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 28.33922261484099,
          "peak_to_trough_decline": 2.3742227247032224,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 28.33922261484099,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 28.33922261484099,
          "peak_to_trough_decline": 2.3742227247032224,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510300.SS|2022",
    "starts": 8,
    "status_counts": {
      "ema_failed": 6,
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 2,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.2974547622434946,
      "terminal_difference": -0.3006650319351307
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 8,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.2974547622434946,
      "terminal_difference": -0.3006650319351307
    },
    "confirmation_rate": 0.25,
    "paired_share": 0.25,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 8,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.20079270153071105,
          "lowest_close_decline": 4.641437007303598,
          "highest_close_rise": 3.034882378049007,
          "peak_to_trough_decline": 5.368781684674876,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.20079270153071105,
          "lowest_close_decline": 4.641437007303598,
          "highest_close_rise": 3.034882378049007,
          "peak_to_trough_decline": 5.368781684674876,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.2974547622434946,
          "lowest_close_decline": 0.2999478351591028,
          "highest_close_rise": 0.974025974025974,
          "peak_to_trough_decline": 0.6693745867514594,
          "intervals": 1.5
        },
        "raw_event_means": {
          "terminal_return": 0.2974547622434946,
          "lowest_close_decline": 0.2999478351591028,
          "highest_close_rise": 0.974025974025974,
          "peak_to_trough_decline": 0.6693745867514594,
          "intervals": 1.5
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.0721848620415235,
          "lowest_close_decline": 2.13501713671168,
          "highest_close_rise": 4.611199235758156,
          "peak_to_trough_decline": 3.0289697746504665,
          "intervals": 18.5
        },
        "raw_event_means": {
          "terminal_return": 4.0721848620415235,
          "lowest_close_decline": 2.13501713671168,
          "highest_close_rise": 4.611199235758156,
          "peak_to_trough_decline": 3.0289697746504665,
          "intervals": 18.5
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.372849893976655,
          "lowest_close_decline": 1.8487084120886939,
          "highest_close_rise": 4.9183044394312,
          "peak_to_trough_decline": 3.388535031847134,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 4.372849893976655,
          "lowest_close_decline": 1.8487084120886939,
          "highest_close_rise": 4.9183044394312,
          "peak_to_trough_decline": 3.388535031847134,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510300.SS|2023",
    "starts": 10,
    "status_counts": {
      "ema_failed": 7,
      "confirmed": 3
    },
    "confirmed": 3,
    "paired_rows": 3,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.3404600149577739,
      "terminal_difference": -0.33640299307715615
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 9,
    "confirmed_mature_price_rows": 3,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.3404600149577739,
      "terminal_difference": -0.33640299307715615
    },
    "confirmation_rate": 0.3,
    "paired_share": 0.3,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 9,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -3.030736554393777,
          "lowest_close_decline": 3.9926080206669448,
          "highest_close_rise": 0.97778542251515,
          "peak_to_trough_decline": 4.929108914795551,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -3.030736554393777,
          "lowest_close_decline": 3.9926080206669448,
          "highest_close_rise": 0.97778542251515,
          "peak_to_trough_decline": 4.929108914795551,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 3,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.3404600149577739,
          "lowest_close_decline": 0.5913325232887808,
          "highest_close_rise": 1.3613933703160483,
          "peak_to_trough_decline": 1.0116673408491186,
          "intervals": 3.0
        },
        "raw_event_means": {
          "terminal_return": 0.3404600149577739,
          "lowest_close_decline": 0.5913325232887808,
          "highest_close_rise": 1.3613933703160483,
          "peak_to_trough_decline": 1.0116673408491186,
          "intervals": 3.0
        }
      },
      "waiting_path": {
        "rows": 3,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.504869248661889,
          "lowest_close_decline": 2.918973635635402,
          "highest_close_rise": 0.5640573542279194,
          "peak_to_trough_decline": 3.4155631178927917,
          "intervals": 17.0
        },
        "raw_event_means": {
          "terminal_return": -0.504869248661889,
          "lowest_close_decline": 2.918973635635402,
          "highest_close_rise": 0.5640573542279194,
          "peak_to_trough_decline": 3.4155631178927917,
          "intervals": 17.0
        }
      },
      "early_paired_path": {
        "rows": 3,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.16846625558473285,
          "lowest_close_decline": 2.5895185880825715,
          "highest_close_rise": 1.7893769094106986,
          "peak_to_trough_decline": 4.304886257442585,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.16846625558473285,
          "lowest_close_decline": 2.5895185880825715,
          "highest_close_rise": 1.7893769094106986,
          "peak_to_trough_decline": 4.304886257442585,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 1,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510300.SS|2024",
    "starts": 6,
    "status_counts": {
      "confirmed": 2,
      "ema_failed": 4
    },
    "confirmed": 2,
    "paired_rows": 2,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.6566870407583323,
      "terminal_difference": -0.6107337248890915
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 5,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.6566870407583323,
      "terminal_difference": -0.6107337248890915
    },
    "confirmation_rate": 0.3333333333333333,
    "paired_share": 0.3333333333333333,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 5,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.175390688291059,
          "lowest_close_decline": 1.9506996279516406,
          "highest_close_rise": 2.890175750922033,
          "peak_to_trough_decline": 3.070635524797293,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.175390688291059,
          "lowest_close_decline": 1.9506996279516406,
          "highest_close_rise": 2.890175750922033,
          "peak_to_trough_decline": 3.070635524797293,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.6566870407583323,
          "lowest_close_decline": 0.16741071428571427,
          "highest_close_rise": 0.8240977550440466,
          "peak_to_trough_decline": 0.16741071428571427,
          "intervals": 2.5
        },
        "raw_event_means": {
          "terminal_return": 0.6566870407583323,
          "lowest_close_decline": 0.16741071428571427,
          "highest_close_rise": 0.8240977550440466,
          "peak_to_trough_decline": 0.16741071428571427,
          "intervals": 2.5
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -1.5081579119552222,
          "lowest_close_decline": 4.055750297173587,
          "highest_close_rise": 1.3853282496327006,
          "peak_to_trough_decline": 4.358762597984322,
          "intervals": 17.5
        },
        "raw_event_means": {
          "terminal_return": -1.5081579119552222,
          "lowest_close_decline": 4.055750297173587,
          "highest_close_rise": 1.3853282496327006,
          "peak_to_trough_decline": 4.358762597984322,
          "intervals": 17.5
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.8974241870661307,
          "lowest_close_decline": 3.4364866870661306,
          "highest_close_rise": 2.0437522835221045,
          "peak_to_trough_decline": 4.521205357142858,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.8974241870661307,
          "lowest_close_decline": 3.4364866870661306,
          "highest_close_rise": 2.0437522835221045,
          "peak_to_trough_decline": 4.521205357142858,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 1,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510300.SS|2025",
    "starts": 8,
    "status_counts": {
      "ema_failed": 4,
      "confirmed": 4
    },
    "confirmed": 4,
    "paired_rows": 4,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.5629280350590884,
      "terminal_difference": -0.584669017648093
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 6,
    "confirmed_mature_price_rows": 4,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.5629280350590884,
      "terminal_difference": -0.584669017648093
    },
    "confirmation_rate": 0.5,
    "paired_share": 0.5,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 6,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.7446276077243084,
          "lowest_close_decline": 1.1599916446226786,
          "highest_close_rise": 3.148949200227586,
          "peak_to_trough_decline": 2.6620079681329627,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.7446276077243084,
          "lowest_close_decline": 1.1599916446226786,
          "highest_close_rise": 3.148949200227586,
          "peak_to_trough_decline": 2.6620079681329627,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 4,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.5629280350590884,
          "lowest_close_decline": 0.05202913631633715,
          "highest_close_rise": 0.5947589492429437,
          "peak_to_trough_decline": 0.08367470593659032,
          "intervals": 1.5
        },
        "raw_event_means": {
          "terminal_return": 0.5629280350590884,
          "lowest_close_decline": 0.05202913631633715,
          "highest_close_rise": 0.5947589492429437,
          "peak_to_trough_decline": 0.08367470593659032,
          "intervals": 1.5
        }
      },
      "waiting_path": {
        "rows": 4,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.0110622082571576,
          "lowest_close_decline": 1.6568396744464318,
          "highest_close_rise": 2.4291944632732196,
          "peak_to_trough_decline": 2.8000689820030527,
          "intervals": 18.5
        },
        "raw_event_means": {
          "terminal_return": 1.0110622082571576,
          "lowest_close_decline": 1.6568396744464318,
          "highest_close_rise": 2.4291944632732196,
          "peak_to_trough_decline": 2.8000689820030527,
          "intervals": 18.5
        }
      },
      "early_paired_path": {
        "rows": 4,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.5957312259052507,
          "lowest_close_decline": 1.3655482576762545,
          "highest_close_rise": 3.016197022944792,
          "peak_to_trough_decline": 2.8000689820030527,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.5957312259052507,
          "lowest_close_decline": 1.3655482576762545,
          "highest_close_rise": 3.016197022944792,
          "peak_to_trough_decline": 2.8000689820030527,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510300.SS|2026",
    "starts": 4,
    "status_counts": {
      "ema_failed": 2,
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 2,
    "expected_assets": [
      "510300.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.1763134871298981,
      "terminal_difference": -1.2591423691280923
    },
    "supported_assets": [
      "510300.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 4,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.1763134871298981,
      "terminal_difference": -1.2591423691280923
    },
    "confirmation_rate": 0.5,
    "paired_share": 0.5,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 4,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.6680910175973427,
          "lowest_close_decline": 2.7025726856272985,
          "highest_close_rise": 2.623567816655942,
          "peak_to_trough_decline": 3.370948156089663,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.6680910175973427,
          "lowest_close_decline": 2.7025726856272985,
          "highest_close_rise": 2.623567816655942,
          "peak_to_trough_decline": 3.370948156089663,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.1763134871298981,
          "lowest_close_decline": 0.15789473684210525,
          "highest_close_rise": 1.531058617672791,
          "peak_to_trough_decline": 0.34889643463497455,
          "intervals": 2.5
        },
        "raw_event_means": {
          "terminal_return": 1.1763134871298981,
          "lowest_close_decline": 0.15789473684210525,
          "highest_close_rise": 1.531058617672791,
          "peak_to_trough_decline": 0.34889643463497455,
          "intervals": 2.5
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.8484645747407664,
          "lowest_close_decline": 3.2206969376979937,
          "highest_close_rise": 2.9395543705618037,
          "peak_to_trough_decline": 3.6862883113796903,
          "intervals": 17.5
        },
        "raw_event_means": {
          "terminal_return": 0.8484645747407664,
          "lowest_close_decline": 3.2206969376979937,
          "highest_close_rise": 2.9395543705618037,
          "peak_to_trough_decline": 3.6862883113796903,
          "intervals": 17.5
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510300.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510300.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.1076069438688587,
          "lowest_close_decline": 3.3684210526315788,
          "highest_close_rise": 4.308836395450569,
          "peak_to_trough_decline": 3.794527891126694,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.1076069438688587,
          "lowest_close_decline": 3.3684210526315788,
          "highest_close_rise": 4.308836395450569,
          "peak_to_trough_decline": 3.794527891126694,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS|2022",
    "starts": 6,
    "status_counts": {
      "ema_failed": 5,
      "confirmed": 1
    },
    "confirmed": 1,
    "paired_rows": 1,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.513975155279503,
      "terminal_difference": -1.5710711480039898
    },
    "supported_assets": [
      "510050.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 6,
    "confirmed_mature_price_rows": 1,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.513975155279503,
      "terminal_difference": -1.5710711480039898
    },
    "confirmation_rate": 0.16666666666666666,
    "paired_share": 0.16666666666666666,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 6,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.07179553087099692,
          "lowest_close_decline": 4.495124314056052,
          "highest_close_rise": 3.4619487520409304,
          "peak_to_trough_decline": 5.1472108824368,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.07179553087099692,
          "lowest_close_decline": 4.495124314056052,
          "highest_close_rise": 3.4619487520409304,
          "peak_to_trough_decline": 5.1472108824368,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.513975155279503,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.9021739130434783,
          "peak_to_trough_decline": 0.38095238095238093,
          "intervals": 2.0
        },
        "raw_event_means": {
          "terminal_return": 1.513975155279503,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.9021739130434783,
          "peak_to_trough_decline": 0.38095238095238093,
          "intervals": 2.0
        }
      },
      "waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.7712635194430075,
          "lowest_close_decline": 2.8680688336520075,
          "highest_close_rise": 5.012175489780144,
          "peak_to_trough_decline": 2.8680688336520075,
          "intervals": 18.0
        },
        "raw_event_means": {
          "terminal_return": 3.7712635194430075,
          "lowest_close_decline": 2.8680688336520075,
          "highest_close_rise": 5.012175489780144,
          "peak_to_trough_decline": 2.8680688336520075,
          "intervals": 18.0
        }
      },
      "early_paired_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 5.342334667446997,
          "lowest_close_decline": 1.3975155279503106,
          "highest_close_rise": 6.602033736713927,
          "peak_to_trough_decline": 3.238095238095238,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 5.342334667446997,
          "lowest_close_decline": 1.3975155279503106,
          "highest_close_rise": 6.602033736713927,
          "peak_to_trough_decline": 3.238095238095238,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS|2023",
    "starts": 8,
    "status_counts": {
      "ema_failed": 8
    },
    "confirmed": 0,
    "paired_rows": 0,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": null,
      "terminal_difference": null
    },
    "supported_assets": [],
    "missing_assets": [
      "510050.SS"
    ],
    "numeric_rows": 7,
    "confirmed_mature_price_rows": 0,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": null,
      "terminal_difference": null
    },
    "confirmation_rate": 0.0,
    "paired_share": 0.0,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 7,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -2.5020234366377037,
          "lowest_close_decline": 4.172181277202627,
          "highest_close_rise": 0.7898327649718723,
          "peak_to_trough_decline": 4.924778162376829,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -2.5020234366377037,
          "lowest_close_decline": 4.172181277202627,
          "highest_close_rise": 0.7898327649718723,
          "peak_to_trough_decline": 4.924778162376829,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 0,
        "supported_assets": [],
        "supported_asset_count": 0,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [
          "510050.SS"
        ],
        "values": {
          "terminal_return": null,
          "lowest_close_decline": null,
          "highest_close_rise": null,
          "peak_to_trough_decline": null,
          "intervals": null
        },
        "raw_event_means": {
          "terminal_return": null,
          "lowest_close_decline": null,
          "highest_close_rise": null,
          "peak_to_trough_decline": null,
          "intervals": null
        }
      },
      "waiting_path": {
        "rows": 0,
        "supported_assets": [],
        "supported_asset_count": 0,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [
          "510050.SS"
        ],
        "values": {
          "terminal_return": null,
          "lowest_close_decline": null,
          "highest_close_rise": null,
          "peak_to_trough_decline": null,
          "intervals": null
        },
        "raw_event_means": {
          "terminal_return": null,
          "lowest_close_decline": null,
          "highest_close_rise": null,
          "peak_to_trough_decline": null,
          "intervals": null
        }
      },
      "early_paired_path": {
        "rows": 0,
        "supported_assets": [],
        "supported_asset_count": 0,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [
          "510050.SS"
        ],
        "values": {
          "terminal_return": null,
          "lowest_close_decline": null,
          "highest_close_rise": null,
          "peak_to_trough_decline": null,
          "intervals": null
        },
        "raw_event_means": {
          "terminal_return": null,
          "lowest_close_decline": null,
          "highest_close_rise": null,
          "peak_to_trough_decline": null,
          "intervals": null
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 1,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS|2024",
    "starts": 6,
    "status_counts": {
      "confirmed": 2,
      "ema_failed": 4
    },
    "confirmed": 2,
    "paired_rows": 2,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.7175061474667981,
      "terminal_difference": -0.7415186364138806
    },
    "supported_assets": [
      "510050.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 3,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.7175061474667981,
      "terminal_difference": -0.7415186364138806
    },
    "confirmation_rate": 0.3333333333333333,
    "paired_share": 0.3333333333333333,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 3,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.0644692336333748,
          "lowest_close_decline": 3.221505844235791,
          "highest_close_rise": 3.242974389964289,
          "peak_to_trough_decline": 3.6925585250248076,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 1.0644692336333748,
          "lowest_close_decline": 3.221505844235791,
          "highest_close_rise": 3.242974389964289,
          "peak_to_trough_decline": 3.6925585250248076,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.7175061474667981,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 0.7175061474667981,
          "peak_to_trough_decline": 0.0,
          "intervals": 1.5
        },
        "raw_event_means": {
          "terminal_return": 0.7175061474667981,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 0.7175061474667981,
          "peak_to_trough_decline": 0.0,
          "intervals": 1.5
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.718170899107756,
          "lowest_close_decline": 2.410003431708991,
          "highest_close_rise": 4.122426218256692,
          "peak_to_trough_decline": 2.410003431708991,
          "intervals": 18.5
        },
        "raw_event_means": {
          "terminal_return": 3.718170899107756,
          "lowest_close_decline": 2.410003431708991,
          "highest_close_rise": 4.122426218256692,
          "peak_to_trough_decline": 2.410003431708991,
          "intervals": 18.5
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.459689535521637,
          "lowest_close_decline": 1.7034244105254657,
          "highest_close_rise": 4.864461584946434,
          "peak_to_trough_decline": 2.410003431708991,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 4.459689535521637,
          "lowest_close_decline": 1.7034244105254657,
          "highest_close_rise": 4.864461584946434,
          "peak_to_trough_decline": 2.410003431708991,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 3,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS|2025",
    "starts": 6,
    "status_counts": {
      "ema_failed": 3,
      "confirmed": 3
    },
    "confirmed": 3,
    "paired_rows": 2,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.9177238099334921,
      "terminal_difference": -0.9393464352369579
    },
    "supported_assets": [
      "510050.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 4,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.9177238099334921,
      "terminal_difference": -0.9393464352369579
    },
    "confirmation_rate": 0.5,
    "paired_share": 0.3333333333333333,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 4,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.760905882921916,
          "lowest_close_decline": 0.47451370892919986,
          "highest_close_rise": 3.6779414775675368,
          "peak_to_trough_decline": 1.700461935103458,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.760905882921916,
          "lowest_close_decline": 0.47451370892919986,
          "highest_close_rise": 3.6779414775675368,
          "peak_to_trough_decline": 1.700461935103458,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.9177238099334921,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 0.9177238099334921,
          "peak_to_trough_decline": 0.0,
          "intervals": 1.0
        },
        "raw_event_means": {
          "terminal_return": 0.9177238099334921,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 0.9177238099334921,
          "peak_to_trough_decline": 0.0,
          "intervals": 1.0
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.6665584937383329,
          "lowest_close_decline": 0.6532485875706214,
          "highest_close_rise": 2.8153549926442407,
          "peak_to_trough_decline": 1.8957051015926307,
          "intervals": 19.0
        },
        "raw_event_means": {
          "terminal_return": 1.6665584937383329,
          "lowest_close_decline": 0.6532485875706214,
          "highest_close_rise": 2.8153549926442407,
          "peak_to_trough_decline": 1.8957051015926307,
          "intervals": 19.0
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.6059049289752907,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 3.759328583314361,
          "peak_to_trough_decline": 1.8957051015926307,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.6059049289752907,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 3.759328583314361,
          "peak_to_trough_decline": 1.8957051015926307,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510050.SS|2026",
    "starts": 5,
    "status_counts": {
      "ema_failed": 3,
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 1,
    "expected_assets": [
      "510050.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.1440107671601616,
      "terminal_difference": -1.1698899195776238
    },
    "supported_assets": [
      "510050.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 4,
    "confirmed_mature_price_rows": 1,
    "immature_outcomes": 1,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.1440107671601616,
      "terminal_difference": -1.1698899195776238
    },
    "confirmation_rate": 0.4,
    "paired_share": 0.2,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 4,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.341177459745432,
          "lowest_close_decline": 1.9327523634165937,
          "highest_close_rise": 2.893895243723202,
          "peak_to_trough_decline": 2.842221630071095,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.341177459745432,
          "lowest_close_decline": 1.9327523634165937,
          "highest_close_rise": 2.893895243723202,
          "peak_to_trough_decline": 2.842221630071095,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.1440107671601616,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.4131897711978465,
          "peak_to_trough_decline": 1.06171201061712,
          "intervals": 6.0
        },
        "raw_event_means": {
          "terminal_return": 1.1440107671601616,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 1.4131897711978465,
          "peak_to_trough_decline": 1.06171201061712,
          "intervals": 6.0
        }
      },
      "waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.2621423819028608,
          "lowest_close_decline": 0.16633399866932802,
          "highest_close_rise": 3.8922155688622753,
          "peak_to_trough_decline": 1.569004162664105,
          "intervals": 14.0
        },
        "raw_event_means": {
          "terminal_return": 2.2621423819028608,
          "lowest_close_decline": 0.16633399866932802,
          "highest_close_rise": 3.8922155688622753,
          "peak_to_trough_decline": 1.569004162664105,
          "intervals": 14.0
        }
      },
      "early_paired_path": {
        "rows": 1,
        "supported_assets": [
          "510050.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510050.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.4320323014804845,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 5.0807537012113055,
          "peak_to_trough_decline": 1.569004162664105,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 3.4320323014804845,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 5.0807537012113055,
          "peak_to_trough_decline": 1.569004162664105,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 1
  },
  {
    "group": "510500.SS|2022",
    "starts": 10,
    "status_counts": {
      "ema_failed": 6,
      "confirmed": 4
    },
    "confirmed": 4,
    "paired_rows": 4,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": -0.4089220314904918,
      "terminal_difference": 0.43588137524706116
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 10,
    "confirmed_mature_price_rows": 4,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": -0.4089220314904918,
      "terminal_difference": 0.43588137524706116
    },
    "confirmation_rate": 0.4,
    "paired_share": 0.4,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 10,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -1.9713653332032757,
          "lowest_close_decline": 6.891732171537169,
          "highest_close_rise": 2.660681240526595,
          "peak_to_trough_decline": 8.108837772066193,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -1.9713653332032757,
          "lowest_close_decline": 6.891732171537169,
          "highest_close_rise": 2.660681240526595,
          "peak_to_trough_decline": 8.108837772066193,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 4,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.4089220314904918,
          "lowest_close_decline": 0.49129765749287135,
          "highest_close_rise": 0.978015642968444,
          "peak_to_trough_decline": 1.3579541283441527,
          "intervals": 3.25
        },
        "raw_event_means": {
          "terminal_return": -0.4089220314904918,
          "lowest_close_decline": 0.49129765749287135,
          "highest_close_rise": 0.978015642968444,
          "peak_to_trough_decline": 1.3579541283441527,
          "intervals": 3.25
        }
      },
      "waiting_path": {
        "rows": 4,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.5662220489621401,
          "lowest_close_decline": 4.674907906558301,
          "highest_close_rise": 4.175833022157929,
          "peak_to_trough_decline": 5.907757527712529,
          "intervals": 16.75
        },
        "raw_event_means": {
          "terminal_return": 0.5662220489621401,
          "lowest_close_decline": 4.674907906558301,
          "highest_close_rise": 4.175833022157929,
          "peak_to_trough_decline": 5.907757527712529,
          "intervals": 16.75
        }
      },
      "early_paired_path": {
        "rows": 4,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.13034067371507896,
          "lowest_close_decline": 5.0783798442069585,
          "highest_close_rise": 3.7430173214423017,
          "peak_to_trough_decline": 6.65024021965246,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.13034067371507896,
          "lowest_close_decline": 5.0783798442069585,
          "highest_close_rise": 3.7430173214423017,
          "peak_to_trough_decline": 6.65024021965246,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510500.SS|2023",
    "starts": 10,
    "status_counts": {
      "confirmed": 4,
      "ema_failed": 6
    },
    "confirmed": 4,
    "paired_rows": 4,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.2067371508146805,
      "terminal_difference": -1.2081799979504908
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 8,
    "confirmed_mature_price_rows": 4,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.2067371508146805,
      "terminal_difference": -1.2081799979504908
    },
    "confirmation_rate": 0.4,
    "paired_share": 0.4,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 8,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.17740338450932422,
          "lowest_close_decline": 2.019128877326928,
          "highest_close_rise": 2.0226556115868153,
          "peak_to_trough_decline": 3.253241824884345,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -0.17740338450932422,
          "lowest_close_decline": 2.019128877326928,
          "highest_close_rise": 2.0226556115868153,
          "peak_to_trough_decline": 3.253241824884345,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 4,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.2067371508146805,
          "lowest_close_decline": 0.18661933231948163,
          "highest_close_rise": 1.2067371508146805,
          "peak_to_trough_decline": 0.29774801457294925,
          "intervals": 4.0
        },
        "raw_event_means": {
          "terminal_return": 1.2067371508146805,
          "lowest_close_decline": 0.18661933231948163,
          "highest_close_rise": 1.2067371508146805,
          "peak_to_trough_decline": 0.29774801457294925,
          "intervals": 4.0
        }
      },
      "waiting_path": {
        "rows": 4,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.7919981663075231,
          "lowest_close_decline": 2.809290426155357,
          "highest_close_rise": 1.29926460512175,
          "peak_to_trough_decline": 3.533568632494353,
          "intervals": 16.0
        },
        "raw_event_means": {
          "terminal_return": -0.7919981663075231,
          "lowest_close_decline": 2.809290426155357,
          "highest_close_rise": 1.29926460512175,
          "peak_to_trough_decline": 3.533568632494353,
          "intervals": 16.0
        }
      },
      "early_paired_path": {
        "rows": 4,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.41618183164296774,
          "lowest_close_decline": 2.1207052603709604,
          "highest_close_rise": 2.5260139866761326,
          "peak_to_trough_decline": 3.533568632494353,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.41618183164296774,
          "lowest_close_decline": 2.1207052603709604,
          "highest_close_rise": 2.5260139866761326,
          "peak_to_trough_decline": 3.533568632494353,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510500.SS|2024",
    "starts": 5,
    "status_counts": {
      "confirmed": 1,
      "ema_failed": 4
    },
    "confirmed": 1,
    "paired_rows": 1,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.6096399314155078,
      "terminal_difference": -0.6405779169522159
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 5,
    "confirmed_mature_price_rows": 1,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.6096399314155078,
      "terminal_difference": -0.6405779169522159
    },
    "confirmation_rate": 0.2,
    "paired_share": 0.2,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 5,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 9.102184862150066,
          "lowest_close_decline": 1.3849733777365787,
          "highest_close_rise": 11.407350984753078,
          "peak_to_trough_decline": 3.3472891664011657,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 9.102184862150066,
          "lowest_close_decline": 1.3849733777365787,
          "highest_close_rise": 11.407350984753078,
          "peak_to_trough_decline": 3.3472891664011657,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.6096399314155078,
          "lowest_close_decline": 0.7048961706991808,
          "highest_close_rise": 0.6096399314155078,
          "peak_to_trough_decline": 0.7048961706991808,
          "intervals": 5.0
        },
        "raw_event_means": {
          "terminal_return": 0.6096399314155078,
          "lowest_close_decline": 0.7048961706991808,
          "highest_close_rise": 0.6096399314155078,
          "peak_to_trough_decline": 0.7048961706991808,
          "intervals": 5.0
        }
      },
      "waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 5.074796440068169,
          "lowest_close_decline": 0.4165877674682825,
          "highest_close_rise": 5.074796440068169,
          "peak_to_trough_decline": 2.5750277880696553,
          "intervals": 15.0
        },
        "raw_event_means": {
          "terminal_return": 5.074796440068169,
          "lowest_close_decline": 0.4165877674682825,
          "highest_close_rise": 5.074796440068169,
          "peak_to_trough_decline": 2.5750277880696553,
          "intervals": 15.0
        }
      },
      "early_paired_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 5.7153743570203845,
          "lowest_close_decline": 0.7048961706991808,
          "highest_close_rise": 5.7153743570203845,
          "peak_to_trough_decline": 2.5750277880696553,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 5.7153743570203845,
          "lowest_close_decline": 0.7048961706991808,
          "highest_close_rise": 5.7153743570203845,
          "peak_to_trough_decline": 2.5750277880696553,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510500.SS|2025",
    "starts": 6,
    "status_counts": {
      "ema_failed": 4,
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 2,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": -0.76475990406273,
      "terminal_difference": 0.7562564762262394
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 4,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": -0.76475990406273,
      "terminal_difference": 0.7562564762262394
    },
    "confirmation_rate": 0.3333333333333333,
    "paired_share": 0.3333333333333333,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 4,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.81797424511842,
          "lowest_close_decline": 2.3539427649412685,
          "highest_close_rise": 4.315124696485054,
          "peak_to_trough_decline": 3.699541960808116,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.81797424511842,
          "lowest_close_decline": 2.3539427649412685,
          "highest_close_rise": 4.315124696485054,
          "peak_to_trough_decline": 3.699541960808116,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.76475990406273,
          "lowest_close_decline": 0.76475990406273,
          "highest_close_rise": 0.2627134669789683,
          "peak_to_trough_decline": 1.0251063637194997,
          "intervals": 2.5
        },
        "raw_event_means": {
          "terminal_return": -0.76475990406273,
          "lowest_close_decline": 0.76475990406273,
          "highest_close_rise": 0.2627134669789683,
          "peak_to_trough_decline": 1.0251063637194997,
          "intervals": 2.5
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -0.3921635732402453,
          "lowest_close_decline": 3.5880846994223834,
          "highest_close_rise": 1.4227099708339512,
          "peak_to_trough_decline": 4.939145701672771,
          "intervals": 17.5
        },
        "raw_event_means": {
          "terminal_return": -0.3921635732402453,
          "lowest_close_decline": 3.5880846994223834,
          "highest_close_rise": 1.4227099708339512,
          "peak_to_trough_decline": 4.939145701672771,
          "intervals": 17.5
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -1.1484200494664847,
          "lowest_close_decline": 4.3169829001739375,
          "highest_close_rise": 0.6468545625436483,
          "peak_to_trough_decline": 4.939145701672771,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -1.1484200494664847,
          "lowest_close_decline": 4.3169829001739375,
          "highest_close_rise": 0.6468545625436483,
          "peak_to_trough_decline": 4.939145701672771,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "510500.SS|2026",
    "starts": 2,
    "status_counts": {
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 1,
    "expected_assets": [
      "510500.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 3.6288297338021094,
      "terminal_difference": -3.8966059737009937
    },
    "supported_assets": [
      "510500.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 1,
    "confirmed_mature_price_rows": 1,
    "immature_outcomes": 1,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 3.6288297338021094,
      "terminal_difference": -3.8966059737009937
    },
    "confirmation_rate": 1.0,
    "paired_share": 0.5,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 11.275740833751884,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 11.903566047212456,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 11.275740833751884,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 11.903566047212456,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.6288297338021094,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 3.6288297338021094,
          "peak_to_trough_decline": 0.5883073906115945,
          "intervals": 5.0
        },
        "raw_event_means": {
          "terminal_return": 3.6288297338021094,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 3.6288297338021094,
          "peak_to_trough_decline": 0.5883073906115945,
          "intervals": 5.0
        }
      },
      "waiting_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 7.379134860050891,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 7.9849751605476795,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 15.0
        },
        "raw_event_means": {
          "terminal_return": 7.379134860050891,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 7.9849751605476795,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 15.0
        }
      },
      "early_paired_path": {
        "rows": 1,
        "supported_assets": [
          "510500.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "510500.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 11.275740833751884,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 11.903566047212456,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 11.275740833751884,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 11.903566047212456,
          "peak_to_trough_decline": 2.1525724423418096,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 1
  },
  {
    "group": "588000.SS|2022",
    "starts": 5,
    "status_counts": {
      "ema_failed": 2,
      "confirmed": 3
    },
    "confirmed": 3,
    "paired_rows": 3,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 1.9116084887104303,
      "terminal_difference": -1.9540369253762357
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 5,
    "confirmed_mature_price_rows": 3,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 1.9116084887104303,
      "terminal_difference": -1.9540369253762357
    },
    "confirmation_rate": 0.6,
    "paired_share": 0.6,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 5,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -1.385269239790325,
          "lowest_close_decline": 5.102056994351784,
          "highest_close_rise": 6.4469042905418705,
          "peak_to_trough_decline": 8.599652153666046,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -1.385269239790325,
          "lowest_close_decline": 5.102056994351784,
          "highest_close_rise": 6.4469042905418705,
          "peak_to_trough_decline": 8.599652153666046,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.9116084887104303,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 2.0423206445942106,
          "peak_to_trough_decline": 0.12671313515747387,
          "intervals": 2.0
        },
        "raw_event_means": {
          "terminal_return": 1.9116084887104303,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 2.0423206445942106,
          "peak_to_trough_decline": 0.12671313515747387,
          "intervals": 2.0
        }
      },
      "waiting_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.086625162454967,
          "lowest_close_decline": 2.124239133337515,
          "highest_close_rise": 7.876118623087161,
          "peak_to_trough_decline": 6.2114480124709095,
          "intervals": 18.0
        },
        "raw_event_means": {
          "terminal_return": 2.086625162454967,
          "lowest_close_decline": 2.124239133337515,
          "highest_close_rise": 7.876118623087161,
          "peak_to_trough_decline": 6.2114480124709095,
          "intervals": 18.0
        }
      },
      "early_paired_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.040662087831203,
          "lowest_close_decline": 1.1007982824621194,
          "highest_close_rise": 9.92862142157189,
          "peak_to_trough_decline": 6.2114480124709095,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 4.040662087831203,
          "lowest_close_decline": 1.1007982824621194,
          "highest_close_rise": 9.92862142157189,
          "peak_to_trough_decline": 6.2114480124709095,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "588000.SS|2023",
    "starts": 11,
    "status_counts": {
      "ema_failed": 9,
      "confirmed": 2
    },
    "confirmed": 2,
    "paired_rows": 2,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.00795433916521407,
      "terminal_difference": -0.008123759339491388
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 9,
    "confirmed_mature_price_rows": 2,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.00795433916521407,
      "terminal_difference": -0.008123759339491388
    },
    "confirmation_rate": 0.18181818181818182,
    "paired_share": 0.18181818181818182,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 9,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.7563064805001408,
          "lowest_close_decline": 4.191577725298268,
          "highest_close_rise": 4.133710067562702,
          "peak_to_trough_decline": 5.342946461422133,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.7563064805001408,
          "lowest_close_decline": 4.191577725298268,
          "highest_close_rise": 4.133710067562702,
          "peak_to_trough_decline": 5.342946461422133,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 2,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.00795433916521407,
          "lowest_close_decline": 0.04557885141294439,
          "highest_close_rise": 0.19026974481699166,
          "peak_to_trough_decline": 0.18181818181818182,
          "intervals": 2.0
        },
        "raw_event_means": {
          "terminal_return": 0.00795433916521407,
          "lowest_close_decline": 0.04557885141294439,
          "highest_close_rise": 0.19026974481699166,
          "peak_to_trough_decline": 0.18181818181818182,
          "intervals": 2.0
        }
      },
      "waiting_path": {
        "rows": 2,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -3.5581014091104257,
          "lowest_close_decline": 3.7862035988914475,
          "highest_close_rise": 0.816337483898669,
          "peak_to_trough_decline": 4.566480981156857,
          "intervals": 18.0
        },
        "raw_event_means": {
          "terminal_return": -3.5581014091104257,
          "lowest_close_decline": 3.7862035988914475,
          "highest_close_rise": 0.816337483898669,
          "peak_to_trough_decline": 4.566480981156857,
          "intervals": 18.0
        }
      },
      "early_paired_path": {
        "rows": 2,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": -3.549977649770934,
          "lowest_close_decline": 3.7778719068356565,
          "highest_close_rise": 0.824713692589679,
          "peak_to_trough_decline": 4.566480981156857,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": -3.549977649770934,
          "lowest_close_decline": 3.7778719068356565,
          "highest_close_rise": 0.824713692589679,
          "peak_to_trough_decline": 4.566480981156857,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "588000.SS|2024",
    "starts": 7,
    "status_counts": {
      "confirmed": 6,
      "ema_failed": 1
    },
    "confirmed": 6,
    "paired_rows": 5,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 2.6052848060316345,
      "terminal_difference": -3.3579313122757832
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 6,
    "confirmed_mature_price_rows": 5,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 2.6052848060316345,
      "terminal_difference": -3.3579313122757832
    },
    "confirmation_rate": 0.8571428571428571,
    "paired_share": 0.7142857142857143,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 6,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 5.127062752532528,
          "lowest_close_decline": 4.290739100724843,
          "highest_close_rise": 12.801004826846002,
          "peak_to_trough_decline": 8.783582853170639,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 5.127062752532528,
          "lowest_close_decline": 4.290739100724843,
          "highest_close_rise": 12.801004826846002,
          "peak_to_trough_decline": 8.783582853170639,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 5,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.6052848060316345,
          "lowest_close_decline": 0.40496601185277115,
          "highest_close_rise": 3.7420808397621883,
          "peak_to_trough_decline": 1.3109755077189618,
          "intervals": 2.8
        },
        "raw_event_means": {
          "terminal_return": 2.6052848060316345,
          "lowest_close_decline": 0.40496601185277115,
          "highest_close_rise": 3.7420808397621883,
          "peak_to_trough_decline": 1.3109755077189618,
          "intervals": 2.8
        }
      },
      "waiting_path": {
        "rows": 5,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.188713825997725,
          "lowest_close_decline": 3.318094874692418,
          "highest_close_rise": 11.142911195707274,
          "peak_to_trough_decline": 8.693039648849416,
          "intervals": 17.2
        },
        "raw_event_means": {
          "terminal_return": 4.188713825997725,
          "lowest_close_decline": 3.318094874692418,
          "highest_close_rise": 11.142911195707274,
          "peak_to_trough_decline": 8.693039648849416,
          "intervals": 17.2
        }
      },
      "early_paired_path": {
        "rows": 5,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 7.546645138273509,
          "lowest_close_decline": 3.7040200007177213,
          "highest_close_rise": 15.18376599500354,
          "peak_to_trough_decline": 8.932259222799743,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 7.546645138273509,
          "lowest_close_decline": 3.7040200007177213,
          "highest_close_rise": 15.18376599500354,
          "peak_to_trough_decline": 8.932259222799743,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 1,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "588000.SS|2025",
    "starts": 11,
    "status_counts": {
      "ema_failed": 8,
      "confirmed": 3
    },
    "confirmed": 3,
    "paired_rows": 3,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.15128020487833418,
      "terminal_difference": -0.16814072536439348
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 9,
    "confirmed_mature_price_rows": 3,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 0.15128020487833418,
      "terminal_difference": -0.16814072536439348
    },
    "confirmation_rate": 0.2727272727272727,
    "paired_share": 0.2727272727272727,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 9,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.59084519291503,
          "lowest_close_decline": 2.885675089272301,
          "highest_close_rise": 6.408222989614419,
          "peak_to_trough_decline": 4.841430877587744,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 3.59084519291503,
          "lowest_close_decline": 2.885675089272301,
          "highest_close_rise": 6.408222989614419,
          "peak_to_trough_decline": 4.841430877587744,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.15128020487833418,
          "lowest_close_decline": 0.22264631043256997,
          "highest_close_rise": 0.37392651531090415,
          "peak_to_trough_decline": 0.22264631043256997,
          "intervals": 1.0
        },
        "raw_event_means": {
          "terminal_return": 0.15128020487833418,
          "lowest_close_decline": 0.22264631043256997,
          "highest_close_rise": 0.37392651531090415,
          "peak_to_trough_decline": 0.22264631043256997,
          "intervals": 1.0
        }
      },
      "waiting_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.045202890625683,
          "lowest_close_decline": 2.482502729027183,
          "highest_close_rise": 4.4643590485271165,
          "peak_to_trough_decline": 4.523820577903402,
          "intervals": 19.0
        },
        "raw_event_means": {
          "terminal_return": 3.045202890625683,
          "lowest_close_decline": 2.482502729027183,
          "highest_close_rise": 4.4643590485271165,
          "peak_to_trough_decline": 4.523820577903402,
          "intervals": 19.0
        }
      },
      "early_paired_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 3.2133436159900763,
          "lowest_close_decline": 2.336246209280195,
          "highest_close_rise": 4.637324642327509,
          "peak_to_trough_decline": 4.523820577903402,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 3.2133436159900763,
          "lowest_close_decline": 2.336246209280195,
          "highest_close_rise": 4.637324642327509,
          "peak_to_trough_decline": 4.523820577903402,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 2,
    "not_yet_terminal_outcomes": 0
  },
  {
    "group": "588000.SS|2026",
    "starts": 3,
    "status_counts": {
      "ema_failed": 2,
      "confirmed": 1
    },
    "confirmed": 1,
    "paired_rows": 1,
    "expected_assets": [
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 4.734982332155477,
      "terminal_difference": -5.802110604044767
    },
    "supported_assets": [
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 3,
    "confirmed_mature_price_rows": 1,
    "immature_outcomes": 0,
    "asset_count": 1,
    "equal_asset_means": {
      "waiting_cost": 4.734982332155477,
      "terminal_difference": -5.802110604044767
    },
    "confirmation_rate": 0.3333333333333333,
    "paired_share": 0.3333333333333333,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 3,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.3188805584961673,
          "lowest_close_decline": 9.724287423091921,
          "highest_close_rise": 9.87663018345569,
          "peak_to_trough_decline": 10.880807319473233,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.3188805584961673,
          "lowest_close_decline": 9.724287423091921,
          "highest_close_rise": 9.87663018345569,
          "peak_to_trough_decline": 10.880807319473233,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 1,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 4.734982332155477,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 4.734982332155477,
          "peak_to_trough_decline": 0.0,
          "intervals": 4.0
        },
        "raw_event_means": {
          "terminal_return": 4.734982332155477,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 4.734982332155477,
          "peak_to_trough_decline": 0.0,
          "intervals": 4.0
        }
      },
      "waiting_path": {
        "rows": 1,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 22.53711201079622,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 22.53711201079622,
          "peak_to_trough_decline": 2.3742227247032224,
          "intervals": 16.0
        },
        "raw_event_means": {
          "terminal_return": 22.53711201079622,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 22.53711201079622,
          "peak_to_trough_decline": 2.3742227247032224,
          "intervals": 16.0
        }
      },
      "early_paired_path": {
        "rows": 1,
        "supported_assets": [
          "588000.SS"
        ],
        "supported_asset_count": 1,
        "expected_assets": [
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 28.33922261484099,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 28.33922261484099,
          "peak_to_trough_decline": 2.3742227247032224,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 28.33922261484099,
          "lowest_close_decline": 0.0,
          "highest_close_rise": 28.33922261484099,
          "peak_to_trough_decline": 2.3742227247032224,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
    "numeric_scope": "start and terminal both within group period",
    "cross_boundary_outcomes": 0,
    "not_yet_terminal_outcomes": 0
  }
]
```

## 相对已有信息的增量

全部早期观察与成功配对的早期观察之间，差的是事后进入比较的机会组成，不能叫新增信息的帮助。同一成功配对起点的等待价格变化减早期价格变化，只描述等待价差；没有拟合或预测增量。缺确认、失败、中断、太晚及未成熟全部留账，缺少的等待价差记为空，不填0。未确认指截至固定终点仍未确认，不表示以后永远不会确认。

```json
{
  "status": "descriptive_only",
  "paired_price_difference": {
    "starts": 137,
    "status_counts": {
      "ema_failed": 88,
      "confirmed": 49
    },
    "confirmed": 49,
    "paired_rows": 47,
    "expected_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.9153578915217401,
      "terminal_difference": -1.0345976710702334
    },
    "supported_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 137,
    "confirmed_mature_price_rows": 47,
    "immature_outcomes": 2,
    "asset_count": 4,
    "equal_asset_means": {
      "waiting_cost": 0.8912617321291028,
      "terminal_difference": -0.9896161601531634
    },
    "confirmation_rate": 0.35766423357664234,
    "paired_share": 0.34306569343065696,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 135,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.7174394717577506,
          "lowest_close_decline": 3.758612915963943,
          "highest_close_rise": 4.232103505492255,
          "peak_to_trough_decline": 5.0631105031934345,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.7292834307023479,
          "lowest_close_decline": 3.7966779373792297,
          "highest_close_rise": 4.303825355604607,
          "peak_to_trough_decline": 5.125172555079126,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.8912617321291028,
          "lowest_close_decline": 0.23195226400546443,
          "highest_close_rise": 1.3194048535233318,
          "peak_to_trough_decline": 0.5226793211604952,
          "intervals": 2.524175824175824
        },
        "raw_event_means": {
          "terminal_return": 0.9153578915217401,
          "lowest_close_decline": 0.2592189063013266,
          "highest_close_rise": 1.3872088850037378,
          "peak_to_trough_decline": 0.5603660230983467,
          "intervals": 2.5319148936170213
        }
      },
      "waiting_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.8898968549062558,
          "lowest_close_decline": 2.4997334824166373,
          "highest_close_rise": 4.323831027785609,
          "peak_to_trough_decline": 4.0807910974445525,
          "intervals": 17.475824175824172
        },
        "raw_event_means": {
          "terminal_return": 1.8681930442745815,
          "lowest_close_decline": 2.656795021917858,
          "highest_close_rise": 4.556466328005622,
          "peak_to_trough_decline": 4.409325444174466,
          "intervals": 17.46808510638298
        }
      },
      "early_paired_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.879513015059419,
          "lowest_close_decline": 2.27872215021388,
          "highest_close_rise": 5.436184932994667,
          "peak_to_trough_decline": 4.2513622446947625,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.9027907153448145,
          "lowest_close_decline": 2.4893760715768973,
          "highest_close_rise": 5.735796875008873,
          "peak_to_trough_decline": 4.589421607000176,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion"
  },
  "prediction_increment": "not_evaluated",
  "account_policy": "not_evaluated"
}
```

## 机会数量、反例和范围

相邻起点的观察窗口会重叠，四只ETF也受到共同市场影响，因此记录数不是独立验证次数。本轮未估计结果可能由巧合造成的范围，也不把某组均值解释成因果效果。

```json
{
  "qualification": {
    "observations": 4340,
    "ready_252": 4340,
    "starts": 137,
    "planned_assets": [
      "510300.SS",
      "510050.SS",
      "510500.SS",
      "588000.SS"
    ],
    "input_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "input_missing_assets": [],
    "actual_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "partial": false,
    "evaluation_rows": 4340,
    "evaluation_dates": 1085,
    "evaluation_kind": "current_state_qualification_only",
    "outcome_values_used": false
  },
  "outcomes": {
    "starts": 137,
    "status_counts": {
      "ema_failed": 88,
      "confirmed": 49
    },
    "confirmed": 49,
    "paired_rows": 47,
    "expected_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "raw_event_means": {
      "waiting_cost": 0.9153578915217401,
      "terminal_difference": -1.0345976710702334
    },
    "supported_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "numeric_rows": 137,
    "confirmed_mature_price_rows": 47,
    "immature_outcomes": 2,
    "asset_count": 4,
    "equal_asset_means": {
      "waiting_cost": 0.8912617321291028,
      "terminal_difference": -0.9896161601531634
    },
    "confirmation_rate": 0.35766423357664234,
    "paired_share": 0.34306569343065696,
    "count_scope": "all starts in group; price numeric scope separately declared",
    "price_path_means": {
      "early_path": {
        "rows": 135,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.7174394717577506,
          "lowest_close_decline": 3.758612915963943,
          "highest_close_rise": 4.232103505492255,
          "peak_to_trough_decline": 5.0631105031934345,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 0.7292834307023479,
          "lowest_close_decline": 3.7966779373792297,
          "highest_close_rise": 4.303825355604607,
          "peak_to_trough_decline": 5.125172555079126,
          "intervals": 20.0
        }
      },
      "before_waiting_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 0.8912617321291028,
          "lowest_close_decline": 0.23195226400546443,
          "highest_close_rise": 1.3194048535233318,
          "peak_to_trough_decline": 0.5226793211604952,
          "intervals": 2.524175824175824
        },
        "raw_event_means": {
          "terminal_return": 0.9153578915217401,
          "lowest_close_decline": 0.2592189063013266,
          "highest_close_rise": 1.3872088850037378,
          "peak_to_trough_decline": 0.5603660230983467,
          "intervals": 2.5319148936170213
        }
      },
      "waiting_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 1.8898968549062558,
          "lowest_close_decline": 2.4997334824166373,
          "highest_close_rise": 4.323831027785609,
          "peak_to_trough_decline": 4.0807910974445525,
          "intervals": 17.475824175824172
        },
        "raw_event_means": {
          "terminal_return": 1.8681930442745815,
          "lowest_close_decline": 2.656795021917858,
          "highest_close_rise": 4.556466328005622,
          "peak_to_trough_decline": 4.409325444174466,
          "intervals": 17.46808510638298
        }
      },
      "early_paired_path": {
        "rows": 47,
        "supported_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "supported_asset_count": 4,
        "expected_assets": [
          "510050.SS",
          "510300.SS",
          "510500.SS",
          "588000.SS"
        ],
        "missing_assets": [],
        "values": {
          "terminal_return": 2.879513015059419,
          "lowest_close_decline": 2.27872215021388,
          "highest_close_rise": 5.436184932994667,
          "peak_to_trough_decline": 4.2513622446947625,
          "intervals": 20.0
        },
        "raw_event_means": {
          "terminal_return": 2.9027907153448145,
          "lowest_close_decline": 2.4893760715768973,
          "highest_close_rise": 5.735796875008873,
          "peak_to_trough_decline": 4.589421607000176,
          "intervals": 20.0
        }
      }
    },
    "weighting": "mean within each supported asset, then equal asset mean; no independence assertion"
  },
  "periods": [
    {
      "group": "2022-2024",
      "starts": 92,
      "status_counts": {
        "ema_failed": 62,
        "confirmed": 30
      },
      "confirmed": 30,
      "paired_rows": 29,
      "expected_assets": [
        "510050.SS",
        "510300.SS",
        "510500.SS",
        "588000.SS"
      ],
      "raw_event_means": {
        "waiting_cost": 0.9812658511869732,
        "terminal_difference": -1.113238006126352
      },
      "supported_assets": [
        "510050.SS",
        "510300.SS",
        "510500.SS",
        "588000.SS"
      ],
      "missing_assets": [],
      "numeric_rows": 87,
      "confirmed_mature_price_rows": 29,
      "immature_outcomes": 0,
      "asset_count": 4,
      "equal_asset_means": {
        "waiting_cost": 0.9253893201327739,
        "terminal_difference": -1.0259572846100125
      },
      "confirmation_rate": 0.32608695652173914,
      "paired_share": 0.31521739130434784,
      "count_scope": "all starts in group; price numeric scope separately declared",
      "price_path_means": {
        "early_path": {
          "rows": 87,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": -0.39498922734966424,
            "lowest_close_decline": 4.423903461755178,
            "highest_close_rise": 3.7065863746518226,
            "peak_to_trough_decline": 5.736789378662937,
            "intervals": 20.0
          },
          "raw_event_means": {
            "terminal_return": -0.3523824979648278,
            "lowest_close_decline": 4.43217896586792,
            "highest_close_rise": 3.788829940944318,
            "peak_to_trough_decline": 5.778198460864012,
            "intervals": 20.0
          }
        },
        "before_waiting_path": {
          "rows": 29,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 0.9253893201327739,
            "lowest_close_decline": 0.24454406281591004,
            "highest_close_rise": 1.4425322287904043,
            "peak_to_trough_decline": 0.5859230264154804,
            "intervals": 2.568253968253968
          },
          "raw_event_means": {
            "terminal_return": 0.9812658511869732,
            "lowest_close_decline": 0.2841816055446315,
            "highest_close_rise": 1.5718679484772695,
            "peak_to_trough_decline": 0.6798580364015608,
            "intervals": 2.7586206896551726
          }
        },
        "waiting_path": {
          "rows": 29,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 1.681080135666086,
            "lowest_close_decline": 3.002157273086283,
            "highest_close_rise": 4.367210854507585,
            "peak_to_trough_decline": 4.4356987312234715,
            "intervals": 17.43174603174603
          },
          "raw_event_means": {
            "terminal_return": 1.34758569798844,
            "lowest_close_decline": 3.093638329011283,
            "highest_close_rise": 4.651483749122105,
            "peak_to_trough_decline": 4.975278154099609,
            "intervals": 17.24137931034483
          }
        },
        "early_paired_path": {
          "rows": 29,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 2.707037420276098,
            "lowest_close_decline": 2.6092608123110708,
            "highest_close_rise": 5.589094269719842,
            "peak_to_trough_decline": 4.711505697530214,
            "intervals": 20.0
          },
          "raw_event_means": {
            "terminal_return": 2.4608237041147922,
            "lowest_close_decline": 2.828371916041922,
            "highest_close_rise": 5.992028355005254,
            "peak_to_trough_decline": 5.2596933435242414,
            "intervals": 20.0
          }
        }
      },
      "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
      "numeric_scope": "start and terminal both within group period",
      "cross_boundary_outcomes": 5,
      "not_yet_terminal_outcomes": 0
    },
    {
      "group": "2025",
      "starts": 31,
      "status_counts": {
        "ema_failed": 19,
        "confirmed": 12
      },
      "confirmed": 12,
      "paired_rows": 11,
      "expected_assets": [
        "510050.SS",
        "510300.SS",
        "510500.SS",
        "588000.SS"
      ],
      "raw_event_means": {
        "waiting_cost": 0.27377096060117084,
        "terminal_difference": -0.2917525604279082
      },
      "supported_assets": [
        "510050.SS",
        "510300.SS",
        "510500.SS",
        "588000.SS"
      ],
      "missing_assets": [],
      "numeric_rows": 23,
      "confirmed_mature_price_rows": 11,
      "immature_outcomes": 0,
      "asset_count": 4,
      "equal_asset_means": {
        "waiting_cost": 0.21679303645204617,
        "terminal_difference": -0.23397492550580126
      },
      "confirmation_rate": 0.3870967741935484,
      "paired_share": 0.3548387096774194,
      "count_scope": "all starts in group; price numeric scope separately declared",
      "price_path_means": {
        "early_path": {
          "rows": 23,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 2.7285882321699186,
            "lowest_close_decline": 1.718530801941362,
            "highest_close_rise": 4.387559590973649,
            "peak_to_trough_decline": 3.2258606854080702,
            "intervals": 20.0
          },
          "raw_event_means": {
            "terminal_return": 2.830473604119237,
            "lowest_close_decline": 1.9236891985508116,
            "highest_close_rise": 4.719128991482853,
            "peak_to_trough_decline": 3.528040925684077,
            "intervals": 20.0
          }
        },
        "before_waiting_path": {
          "rows": 11,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 0.21679303645204617,
            "lowest_close_decline": 0.25985883770290924,
            "highest_close_rise": 0.537280685366577,
            "peak_to_trough_decline": 0.332856845022165,
            "intervals": 1.5
          },
          "raw_event_means": {
            "terminal_return": 0.27377096060117084,
            "lowest_close_decline": 0.21868866224441075,
            "highest_close_rise": 0.5328808997026734,
            "peak_to_trough_decline": 0.2775318620439155,
            "intervals": 1.4545454545454546
          }
        },
        "waiting_path": {
          "rows": 11,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 1.332665004845232,
            "lowest_close_decline": 2.095168922616655,
            "highest_close_rise": 2.7829046188196322,
            "peak_to_trough_decline": 3.5396850907929642,
            "intervals": 18.5
          },
          "raw_event_means": {
            "terminal_return": 1.4298770314456233,
            "lowest_close_decline": 2.0506848598957528,
            "highest_close_rise": 2.8714531750573284,
            "peak_to_trough_decline": 3.4946762971139282,
            "intervals": 18.545454545454547
          }
        },
        "early_paired_path": {
          "rows": 11,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 1.566639930351033,
            "lowest_close_decline": 2.0046943417825966,
            "highest_close_rise": 3.0149262027825774,
            "peak_to_trough_decline": 3.5396850907929642,
            "intervals": 20.0
          },
          "raw_event_means": {
            "terminal_return": 1.7216295918735318,
            "lowest_close_decline": 1.9186270417175886,
            "highest_close_rise": 3.1626480282252474,
            "peak_to_trough_decline": 3.4946762971139282,
            "intervals": 20.0
          }
        }
      },
      "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
      "numeric_scope": "start and terminal both within group period",
      "cross_boundary_outcomes": 8,
      "not_yet_terminal_outcomes": 0
    },
    {
      "group": "2026H1",
      "starts": 14,
      "status_counts": {
        "ema_failed": 7,
        "confirmed": 7
      },
      "confirmed": 7,
      "paired_rows": 5,
      "expected_assets": [
        "510050.SS",
        "510300.SS",
        "510500.SS",
        "588000.SS"
      ],
      "raw_event_means": {
        "waiting_cost": 2.372089961475509,
        "terminal_difference": -2.6773782471159135
      },
      "supported_assets": [
        "510050.SS",
        "510300.SS",
        "510500.SS",
        "588000.SS"
      ],
      "missing_assets": [],
      "numeric_rows": 12,
      "confirmed_mature_price_rows": 5,
      "immature_outcomes": 2,
      "asset_count": 4,
      "equal_asset_means": {
        "waiting_cost": 2.6710340800619115,
        "terminal_difference": -3.031937216612869
      },
      "confirmation_rate": 0.5,
      "paired_share": 0.35714285714285715,
      "count_scope": "all starts in group; price numeric scope separately declared",
      "price_path_means": {
        "early_path": {
          "rows": 12,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 3.150972467397706,
            "lowest_close_decline": 3.5899031180339533,
            "highest_close_rise": 6.824414822761822,
            "peak_to_trough_decline": 4.811637386993951,
            "intervals": 20.0
          },
          "raw_event_means": {
            "terminal_return": 1.3557880348842906,
            "lowest_close_decline": 3.9761802054542774,
            "highest_close_rise": 5.300275736591342,
            "peak_to_trough_decline": 4.970639462117045,
            "intervals": 20.0
          }
        },
        "before_waiting_path": {
          "rows": 5,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 2.6710340800619115,
            "lowest_close_decline": 0.039473684210526314,
            "highest_close_rise": 2.827015113707056,
            "peak_to_trough_decline": 0.4997289589659223,
            "intervals": 4.375
          },
          "raw_event_means": {
            "terminal_return": 2.372089961475509,
            "lowest_close_decline": 0.06315789473684211,
            "highest_close_rise": 2.567823814500203,
            "peak_to_trough_decline": 0.46956245409973274,
            "intervals": 4.0
          }
        },
        "waiting_path": {
          "rows": 5,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 8.256713456872685,
            "lowest_close_decline": 0.8467577340918304,
            "highest_close_rise": 9.338464277691994,
            "peak_to_trough_decline": 2.445521910272207,
            "intervals": 15.625
          },
          "raw_event_means": {
            "terminal_return": 6.775063680446301,
            "lowest_close_decline": 1.3215455748130631,
            "highest_close_rise": 8.058682296265957,
            "peak_to_trough_decline": 2.693675190493704,
            "intervals": 16.0
          }
        },
        "early_paired_path": {
          "rows": 5,
          "supported_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "supported_asset_count": 4,
          "expected_assets": [
            "510050.SS",
            "510300.SS",
            "510500.SS",
            "588000.SS"
          ],
          "missing_assets": [],
          "values": {
            "terminal_return": 11.288650673485554,
            "lowest_close_decline": 0.8421052631578947,
            "highest_close_rise": 12.40809468967883,
            "peak_to_trough_decline": 2.4725818052089577,
            "intervals": 20.0
          },
          "raw_event_means": {
            "terminal_return": 9.452441927562216,
            "lowest_close_decline": 1.3473684210526315,
            "highest_close_rise": 10.788243030833177,
            "peak_to_trough_decline": 2.7369710223925052,
            "intervals": 20.0
          }
        }
      },
      "weighting": "mean within each supported asset, then equal asset mean; no independence assertion",
      "numeric_scope": "start and terminal both within group period",
      "cross_boundary_outcomes": 0,
      "not_yet_terminal_outcomes": 2
    }
  ]
}
```

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四固定国内宽基ETF，保留4340安排日及137个已精确核对起点；历史已见，非完整ETF总体。",
    "source_refs": [
      "docs/experiments/raw/ema-sma-waiting-path-2026-10-02/protocol.md",
      "docs/experiments/raw/ema-sma-waiting-path-2026-10-02/qualification/qualification.json",
      "docs/experiments/raw/ema-sma-confirmation-readiness-2026-10-02/numeric-identity/all-directions-receipt.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "持续E段首次S跟上为公开研究代理；原文EMA稳定上行、熊市底部和完整模块A未被本代理替代。",
    "source_refs": [
      "docs/experiments/raw/ema-sma-waiting-path-2026-10-02/protocol.md",
      "docs/experiments/raw/ema-sma-waiting-path-2026-10-02/qualification/qualification.json",
      "docs/experiments/raw/ema-sma-confirmation-readiness-2026-10-02/numeric-identity/all-directions-receipt.json"
    ]
  },
  "method_fit": {
    "reason": "同一终点、同一配对集合描述价差；全体早期路径与未确认组分别保留。缩短暴露的风险数字变化不叫预测增量。",
    "source_refs": [
      "docs/experiments/raw/ema-sma-waiting-path-2026-10-02/protocol.md",
      "docs/experiments/raw/ema-sma-waiting-path-2026-10-02/qualification/qualification.json",
      "docs/experiments/raw/ema-sma-confirmation-readiness-2026-10-02/numeric-identity/all-directions-receipt.json"
    ]
  },
  "conclusion_scope": {
    "reason": "只回答此有限历史池内等待的价格路径；未估计总体不确定性，不批准交易或更改纪律。",
    "source_refs": [
      "docs/experiments/raw/ema-sma-waiting-path-2026-10-02/protocol.md",
      "docs/experiments/raw/ema-sma-waiting-path-2026-10-02/qualification/qualification.json",
      "docs/experiments/raw/ema-sma-confirmation-readiness-2026-10-02/numeric-identity/all-directions-receipt.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；仅描述当前合同范围；拟合：0；交易许可：无。
全部起点记录见result.json的event_ledger；未覆盖条件和来源限制继续保留，不能以本轮描述替代完整入场规则。
