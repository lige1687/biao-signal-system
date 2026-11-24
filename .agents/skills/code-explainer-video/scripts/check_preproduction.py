"""Read-only document readiness check; not approval, storage, or artistic validation."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def check(manifest, stage):
    errors = []
    try:
        data = json.loads(manifest.read_text())
    except (OSError, ValueError) as exc:
        return {"ready": False, "stage": stage, "missing_or_invalid": [str(exc)]}
    if not isinstance(data, dict):
        return {"ready": False, "stage": stage, "missing_or_invalid": ["索引必须为JSON对象"]}
    docs = data.get('documents', {})
    if not isinstance(docs, dict):
        docs = {}
    def file_path(value, label):
        if not isinstance(value, str) or not value.strip():
            errors.append(label + '：缺文件位置')
            return None
        try:
            path = (manifest.parent / value).resolve()
            if not path.is_file() or path.stat().st_size == 0:
                raise OSError('文件不存在或为空')
        except (OSError, RuntimeError) as exc:
            errors.append(label + '：' + str(exc))
            return None
        return path
    names = ['brief', 'sources', 'script']
    if stage in ('sample', 'full'):
        names += ['style', 'storyboard', 'assets', 'cues', 'style_approval']
    if stage == 'full':
        names += ['sample_approval']
    paths = {key: file_path(docs.get(key), key) for key in names}
    mode = data.get('voice_mode')
    if mode not in ('none', 'narration'):
        errors.append('voice_mode：须明确none或narration')
    if stage != 'content':
        if data.get('script_reviewed') is not True:
            errors.append('文稿口语编辑尚未完成')
        if mode == 'narration':
            voice = data.get('voice') or {}
            if not isinstance(voice, dict):
                voice = {}
            audio = file_path(voice.get('audio'), '配音')
            alignment = file_path(voice.get('alignment'), '声音时间轴')
            duration = voice.get('duration_seconds')
            duration_ok = isinstance(duration, (int, float)) and not isinstance(duration, bool) and math.isfinite(duration) and duration > 0
            if not duration_ok:
                errors.append('配音实际时长缺失或无效')
            if voice.get('alignment_reviewed') is not True:
                errors.append('音文对应尚未人工核对')
            if alignment:
                try:
                    timeline = json.loads(alignment.read_text())
                    for key, path in [('audio_sha256', audio), ('script_sha256', paths.get('script'))]:
                        if path:
                            digest = hashlib.sha256()
                            with path.open('rb') as stream:
                                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                                    digest.update(chunk)
                            if timeline.get(key) != digest.hexdigest():
                                errors.append(key + '：与当前文件不符，需重新对齐')
                    segments = timeline.get('segments')
                    if not isinstance(segments, list) or not segments:
                        raise ValueError('缺短语时间段')
                    last = 0
                    for seg in segments:
                        start, end = seg['start'], seg['end']
                        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (start, end)):
                            raise ValueError('时间必须为有限秒数')
                        if start < last or end <= start or (duration_ok and end > duration):
                            raise ValueError('时间段重叠、倒序或超过配音长度')
                        if not isinstance(seg.get('text'), str) or not seg['text'].strip():
                            raise ValueError('短语文字为空')
                        last = end
                except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                    errors.append('声音时间轴：' + str(exc))
    return {'ready': not errors, 'stage': stage, 'missing_or_invalid': errors,
            'limits': '只核文件与声明；不代表内容正确、审美通过、真实批准或磁盘安全。'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--stage', choices=['content', 'sample', 'full'], required=True)
    args = parser.parse_args()
    result = check(args.manifest, args.stage)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ready'] else 1)
