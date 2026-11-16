// =============================================================================
// 课程阅读副本 · 官方 unitree_ros2 例程，逻辑未改动，只加了注释
// 上游: https://github.com/unitreerobotics/unitree_ros2
// 版本: 668d1ec5a05d1c38d3306bdca7d59f2ba3581a88（与 scripts/install.sh 固定的一致）
// 本文件: ros2_nodes/g1/g1_audio_client.hpp
// 课程位置: 04_audio_led.py（语音与灯）
//
// ▶ 语音客户端：服务名 "voice"，TTS / 音量 / 放音 / 灯带都在这个类里。
//   仅阅读，不参与本仓库编译。
// =============================================================================

#pragma once

#include <rclcpp/node.hpp>
#include <rclcpp/rclcpp.hpp>

#include "base_client.hpp"
#include "common/time_tools.hpp"
#include "common/ut_errror.hpp"
#include "nlohmann/json.hpp"
#include "patch.hpp"
#include "unitree_api/msg/request.hpp"
#include "unitree_api/msg/response.hpp"
namespace unitree::ros2::g1 {

// 1001 = TtsMaker：文字转语音，让机器人自己念
constexpr int32_t ROBOT_API_ID_AUDIO_TTS = 1001;
// 1002 = 语音识别（本课例程没用到）
constexpr int32_t ROBOT_API_ID_AUDIO_ASR = 1002;
// 1003 = PlayStream：开始播放 PCM 流
constexpr int32_t ROBOT_API_ID_AUDIO_START_PLAY = 1003;
// 1004 = PlayStop：停止播放
constexpr int32_t ROBOT_API_ID_AUDIO_STOP_PLAY = 1004;
// 1005 = GetVolume：读当前音量 0–100
constexpr int32_t ROBOT_API_ID_AUDIO_GET_VOLUME = 1005;
// 1006 = SetVolume：设音量 0–100
constexpr int32_t ROBOT_API_ID_AUDIO_SET_VOLUME = 1006;
// 1010 = LedControl：设灯带颜色，R / G / B 各 0–255
constexpr int32_t ROBOT_API_ID_AUDIO_SET_RGB_LED = 1010;

// ▶ 对应 04_audio_led.py 的 client = AudioClient()；注意它自己继承 rclcpp::Node。
class AudioClient : public rclcpp::Node {
  // TTS 序号，每发一次 TtsMaker 加 1（Python 版这里是自乘的 bug，恒为 0）。
  uint32_t tts_index_ = 0;
  // 服务名 "voice"：话题 /api/voice/request 与 /api/voice/response。
  BaseClient base_client_;

 public:
  // ▶ 对应 04_audio_led.py 的 client.Init()：构造时绑好话题并起节点。
  AudioClient()
      : rclcpp::Node("audio_client"),
        base_client_(this, "/api/voice/request", "/api/voice/response") {};

  // ▶ 对应 04_audio_led.py 的 client.TtsMaker(text, speaker)（api 1001）。
  int32_t TtsMaker(const std::string &text, int32_t speaker_id) {
    nlohmann::json js;
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_AUDIO_TTS;
    js["index"] = tts_index_++;
    js["text"] = text;
    js["speaker_id"] = speaker_id;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ 对应 04_audio_led.py --get：client.GetVolume()（api 1005）。
  int32_t GetVolume(uint8_t &volume) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_AUDIO_GET_VOLUME;
    nlohmann::json js;
    auto res = base_client_.Call(req, js);
    if (res == 0) {
      js["volume"].get_to(volume);
    }
    return res;
  }

  // ▶ 对应 04_audio_led.py --volume：client.SetVolume(v)（api 1006）。
  int32_t SetVolume(uint8_t volume) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_AUDIO_SET_VOLUME;
    nlohmann::json js;
    js["volume"] = volume;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ 对应 04_audio_led.py 的 play_wav()：client.PlayStream(app, stream_id, pcm)（api 1003）。
  int32_t PlayStream(const std::string &app_name, const std::string &stream_id,
                     const std::vector<uint8_t> &pcm_data) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_AUDIO_START_PLAY;
    nlohmann::json js;
    js["app_name"] = app_name;
    js["stream_id"] = stream_id;
    req.parameter = js.dump();
    req.binary = pcm_data;
    return base_client_.Call(req);
  }

  // ▶ 对应 play_wav() 的收尾：client.PlayStop(app)（api 1004）。
  int32_t PlayStop(const std::string &app_name) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_AUDIO_STOP_PLAY;
    nlohmann::json js;
    js["app_name"] = app_name;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }

  // ▶ 对应 04_audio_led.py --led：client.LedControl(r, g, b)（api 1010）。
  int32_t LedControl(uint8_t r, uint8_t g, uint8_t b) {
    unitree_api::msg::Request req;
    req.header.identity.api_id = ROBOT_API_ID_AUDIO_SET_RGB_LED;
    nlohmann::json js;
    js["R"] = r;
    js["G"] = g;
    js["B"] = b;
    req.parameter = js.dump();
    return base_client_.Call(req);
  }
};

}  // namespace unitree::ros2::g1
