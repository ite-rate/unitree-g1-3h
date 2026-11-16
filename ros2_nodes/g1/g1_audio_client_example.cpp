// =============================================================================
// 课程阅读副本 · 官方 unitree_ros2 例程，逻辑未改动，只加了注释
// 上游: https://github.com/unitreerobotics/unitree_ros2
// 版本: 668d1ec5a05d1c38d3306bdca7d59f2ba3581a88（与 scripts/install.sh 固定的一致）
// 本文件: ros2_nodes/g1/g1_audio_client_example.cpp
// 课程位置: 04_audio_led.py（语音与灯）
//
// ▶ 语音与灯带例程：TTS、音量、播放 wav、RGB 灯带，全部走 AudioClient。
//   对照 04_audio_led.py 的 --demo 分支看，里面的 sleep 就是演示节奏。
// ▶ include 路径按上游 example 工程的相对结构；若要自己编译，请把 ros2_nodes/g1
//   放回 example/src/src/g1 下。
//   仅阅读，不参与本仓库编译。
// =============================================================================

/**
 * This example demonstrates how to use ROS2 to call audio client api of unitree
 *g1 robot
 **/
#include <fstream>
#include <rclcpp/executors.hpp>
#include <thread>
#include <vector>

#include "common/time_tools.hpp"
#include "g1/g1_audio_client.hpp"

// wave reader start
// ▶ 对应 04_audio_led.py 的 read_wav()：不依赖第三方库，手动解析 RIFF/WAVE 头。
//   WaveHeader 固定 44 字节，下面用 static_assert 卡住。
struct WaveHeader {
  void SeekToDataChunk(std::istream &is) {
    while (is && subchunk2_id != 0x61746164) {
      is.seekg(subchunk2_size, std::istream::cur);
      is.read(reinterpret_cast<char *>(&subchunk2_id), sizeof(int32_t));
      is.read(reinterpret_cast<char *>(&subchunk2_size), sizeof(int32_t));
    }
  }

  int32_t chunk_id;
  int32_t chunk_size;
  int32_t format;
  int32_t subchunk1_id;
  int32_t subchunk1_size;
  int16_t audio_format;
  int16_t num_channels;
  int32_t sample_rate;
  int32_t byte_rate;
  int16_t block_align;
  int16_t bits_per_sample;
  int32_t subchunk2_id;    // a tag of this chunk
  int32_t subchunk2_size;  // size of subchunk2
};

static_assert(sizeof(WaveHeader) == 44, "WaveHeader Should be 44 bytes");

// 逐字段校验 RIFF / WAVE / fmt / data，任何一项不对就返回空，
// 和 Python 版 read_wav() 里的检查一一对应。
std::vector<uint8_t> ReadWaveImpl(std::istream &is, int32_t *sampling_rate,
                                  int8_t *channel_count, bool *is_ok) {
  WaveHeader header{};
  is.read(reinterpret_cast<char *>(&header.chunk_id), sizeof(header.chunk_id));

  //                        F F I R
  if (header.chunk_id != 0x46464952) {
    printf("Expected chunk_id RIFF. Given: 0x%08x\n", header.chunk_id);
    *is_ok = false;
    return {};
  }

  is.read(reinterpret_cast<char *>(&header.chunk_size),
          sizeof(header.chunk_size));

  is.read(reinterpret_cast<char *>(&header.format), sizeof(header.format));

  //                      E V A W
  if (header.format != 0x45564157) {
    printf("Expected format WAVE. Given: 0x%08x\n", header.format);
    *is_ok = false;
    return {};
  }

  is.read(reinterpret_cast<char *>(&header.subchunk1_id),
          sizeof(header.subchunk1_id));

  is.read(reinterpret_cast<char *>(&header.subchunk1_size),
          sizeof(header.subchunk1_size));

  if (header.subchunk1_id == 0x4b4e554a) {
    // skip junk padding
    is.seekg(header.subchunk1_size, std::istream::cur);

    is.read(reinterpret_cast<char *>(&header.subchunk1_id),
            sizeof(header.subchunk1_id));

    is.read(reinterpret_cast<char *>(&header.subchunk1_size),
            sizeof(header.subchunk1_size));
  }

  if (header.subchunk1_id != 0x20746d66) {
    printf("Expected subchunk1_id 0x20746d66. Given: 0x%08x\n",
           header.subchunk1_id);
    *is_ok = false;
    return {};
  }

  if (header.subchunk1_size != 16 &&
      header.subchunk1_size != 18) {  // 16 for PCM
    printf("Expected subchunk1_size 16. Given: %d\n", header.subchunk1_size);
    *is_ok = false;
    return {};
  }

  is.read(reinterpret_cast<char *>(&header.audio_format),
          sizeof(header.audio_format));

  if (header.audio_format != 1) {  // 1 for PCM
    printf("Expected audio_format 1. Given: %d\n", header.audio_format);
    *is_ok = false;
    return {};
  }

  is.read(reinterpret_cast<char *>(&header.num_channels),
          sizeof(header.num_channels));

  *channel_count = static_cast<int8_t>(header.num_channels);

  is.read(reinterpret_cast<char *>(&header.sample_rate),
          sizeof(header.sample_rate));

  is.read(reinterpret_cast<char *>(&header.byte_rate),
          sizeof(header.byte_rate));

  is.read(reinterpret_cast<char *>(&header.block_align),
          sizeof(header.block_align));

  is.read(reinterpret_cast<char *>(&header.bits_per_sample),
          sizeof(header.bits_per_sample));

  if (header.byte_rate !=
      (header.sample_rate * header.num_channels * header.bits_per_sample / 8)) {
    printf("Incorrect byte rate: %d. Expected: %d", header.byte_rate,
           (header.sample_rate * header.num_channels * header.bits_per_sample /
            8));
    *is_ok = false;
    return {};
  }

  if (header.block_align !=
      (header.num_channels * header.bits_per_sample / 8)) {
    printf("Incorrect block align: %d. Expected: %d\n", header.block_align,
           (header.num_channels * header.bits_per_sample / 8));
    *is_ok = false;
    return {};
  }

  if (header.bits_per_sample != 16) {  // we support only 16 bits per sample
    printf("Expected bits_per_sample 16. Given: %d\n", header.bits_per_sample);
    *is_ok = false;
    return {};
  }

  if (header.subchunk1_size == 18) {
    int16_t extra_size = -1;
    is.read(reinterpret_cast<char *>(&extra_size), sizeof(int16_t));
    if (extra_size != 0) {
      printf(
          "Extra size should be 0 for wave from NAudio. Current extra size "
          "%d\n",
          extra_size);
      *is_ok = false;
      return {};
    }
  }

  is.read(reinterpret_cast<char *>(&header.subchunk2_id),
          sizeof(header.subchunk2_id));

  is.read(reinterpret_cast<char *>(&header.subchunk2_size),
          sizeof(header.subchunk2_size));

  header.SeekToDataChunk(is);
  if (!is) {
    *is_ok = false;
    return {};
  }

  *sampling_rate = header.sample_rate;

  // header.subchunk2_size contains the number of bytes in the data.
  // As we assume each sample contains two bytes, so it is divided by 2 here
  std::vector<int16_t> samples(header.subchunk2_size / 2);

  is.read(reinterpret_cast<char *>(samples.data()), header.subchunk2_size);
  if (!is) {
    *is_ok = false;
    return {};
  }

  std::vector<uint8_t> ans(samples.size() * 2);
  for (int32_t i = 0; i != static_cast<int32_t>(samples.size()); ++i) {
    ans[i * 2] = samples[i] & 0xFF;
    ans[i * 2 + 1] = (samples[i] >> 8) & 0xFF;
  }

  *is_ok = true;
  return ans;
}

// ▶ 对应 04_audio_led.py 的 Path(path).read_bytes()：打开文件后交给 ReadWaveImpl。
std::vector<uint8_t> ReadWave(const std::string &filename,
                              int32_t *sampling_rate, int8_t *channel_count,
                              bool *is_ok) {
  std::ifstream is(filename, std::ifstream::binary);
  auto samples = ReadWaveImpl(is, sampling_rate, channel_count, is_ok);
  return samples;
}
// wave reader end

// 取毫秒时间戳，只用来给 PlayStream 生成不重复的 stream_id。
int64_t GetCurrentTimeMillisecond() {
  auto now = std::chrono::high_resolution_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
      now.time_since_epoch());
  return duration.count();
}

// ▶ 对应 04_audio_led.py 的 --demo：按 TTS、音量、放音、灯带四段依次演示。
//   下面的 sleep 是演示节奏：等机器人把话说完、把缓冲播完、看清灯色。
auto Control(std::shared_ptr<unitree::ros2::g1::AudioClient> client,
             const std::string &audio_file_path) {
  // 第 1 步：TtsMaker 文字转语音（api 1001），speaker_id=0 用默认音色。
  /*TTS Example*/
  int32_t ret =
      client->TtsMaker("你好。我是宇树科技的机器人G1。例程启动成功", 0);
  std::cout << "TtsMaker ret:" << ret << std::endl;
  // 睡 10 秒：等机器人把这句约 10 秒的话念完，否则会和后面的放音演示打架。
  std::this_thread::sleep_for(std::chrono::seconds(10));

  // 第 2 步：GetVolume（api 1005）读当前音量，SetVolume（api 1006）设成 100。
  /*Volume Example*/
  uint8_t volume = 0;
  ret = client->GetVolume(volume);
  std::cout << "GetVolume ret:" << ret
            << "  volume = " << std::to_string(volume) << std::endl;
  ret = client->SetVolume(100);
  std::cout << "SetVolume to 100% , ret:" << ret << std::endl;

  // 第 3 步：读 wav 并播放。G1 只接受 16 kHz / 单声道 / 16-bit PCM，格式不对直接跳过。
  /*Audio Play Example*/
  int32_t sample_rate = -1;
  int8_t num_channels = 0;
  bool filestate = false;
  std::vector<uint8_t> pcm =
      ReadWave(audio_file_path, &sample_rate, &num_channels, &filestate);
  std::cout << "pcm data size : " << pcm.size() << std::endl;

  std::cout << "sample_rate = " << sample_rate
            << " num_channels =  " << std::to_string(num_channels)
            << " filestate =" << filestate << std::endl;

  if (filestate && sample_rate == 16000 && num_channels == 1) {
    // PlayStream（api 1003）：app_name="example"，stream_id 用毫秒时间戳保证唯一。
    ret = client->PlayStream(
        "example",
        std::to_string(unitree::common::GetCurrentTimeMilliseconds()), pcm);
    std::cout << "start play ,ret : " << ret << std::endl;
    // 等 3 秒把缓冲播完，再发 PlayStop（api 1004）。
    std::this_thread::sleep_for(std::chrono::seconds(3));
    std::cout << "stop play" << std::endl;
    ret = client->PlayStop("example");
  } else {
    std::cout << "audio file format error, please check!" << std::endl;
  }

  // 第 4 步：灯带（api 1010）。LedControl(R, G, B)，每色停 2 秒，最后停在蓝色。
  /*LED Control Example*/
  std::cout << "led control start" << std::endl;
  // 绿色：R=0 G=255 B=0
  client->LedControl(0, 255, 0);
  std::this_thread::sleep_for(std::chrono::seconds(2));
  // 关灯：RGB 全 0
  client->LedControl(0, 0, 0);
  std::this_thread::sleep_for(std::chrono::seconds(2));
  // 蓝色：R=0 G=0 B=255
  client->LedControl(0, 0, 255);
  std::cout << "led control end" << std::endl;
  std::cout << "finish!" << std::endl;
}

// ▶ 对应 04_audio_led.py 的 main()：第一个参数必须是 wav 文件路径。
int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "Error: Audio file path not provided!\n"
              << "Usage: g1_audio_client_example audio_file_path" << std::endl;
    return 1;
  }
  std::string audio_file_path = argv[1];
  std::cout << "audio file path : " << audio_file_path << std::endl;

  try {
    rclcpp::init(argc, argv);
    // AudioClient 自己就是一个节点，服务名 "voice"，话题 /api/voice/request。
    auto client = std::make_shared<unitree::ros2::g1::AudioClient>();
    auto thread_ = std::thread([client, audio_file_path]() {
      using namespace std::chrono_literals;
      // 等 1 秒让 DDS 发现完成，再开始演示，避免前几条请求超时。
      std::this_thread::sleep_for(1s);
      Control(client, audio_file_path);
    });
    // spin 让节点收应答；演示逻辑在另一个线程里跑。
    rclcpp::spin(client);
    rclcpp::shutdown();
  } catch (const rclcpp::exceptions::RCLError &e) {
    std::cerr << "RCLError caught: " << e.what() << std::endl;
    return 1;
  }
  return 0;
}