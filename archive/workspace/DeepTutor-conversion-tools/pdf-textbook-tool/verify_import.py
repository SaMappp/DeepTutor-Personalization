# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json
import pipeline
from deeptutor_client import DeepTutorClient

ROOT=Path(__file__).resolve().parent
WORKSPACE='REDACTED_WORKSPACE_ID'
COLLECTION='REDACTED_WORKSPACE_ID'


def main():
    current=json.loads((ROOT/'current-book.json').read_text(encoding='utf-8'))
    result=pipeline.process_pdf(current['source'],log=print)
    assert result['reused_output'] and result['output_sha256']==current['output_sha256']
    client=DeepTutorClient()
    try:
        first=client.import_pdf(result,WORKSPACE,COLLECTION)
        total_before=len(client.call('/api/reading/materials',WORKSPACE))
        second=client.import_pdf(result,WORKSPACE,COLLECTION)
        total_after=len(client.call('/api/reading/materials',WORKSPACE))
        assert second['reused_material'] and first['material']['material_id']==second['material']['material_id']
        assert total_before==total_after
        assert len(first['verified_pages'])==349
        assert first['model_selection_before']==first['model_selection_after']
        assert first['model_selection_after']['model']=='gpt-6.1-sol'
        assert first['model_selection_after']['reasoning_effort']=='high'
        assert not first['source_state_differences']
        target=Path(result['output']).parent
        material=first['material']
        position=client.call('/api/reading/materials/'+material['material_id']+'/position',WORKSPACE)
        summary={'material_id':material['material_id'],'pages_verified':349,
                 'char_count':material['char_count'],'duplicate_material_count_unchanged':total_before==total_after,
                 'materials_total':total_after,'model':first['model_selection_after'],
                 'source_material_states_unchanged':not first['source_state_differences'],
                 'new_material_position':position,'url':first['url']}
        pipeline.atomic_json(ROOT/'verification'/'import-results.json',summary)
        # Compatible concise delivery record for the original book task.
        pipeline.atomic_json(target/'DeepTutor导入记录.json',{
            'base':first['base'],'workspace_id':WORKSPACE,'collection_id':COLLECTION,
            'collection_title':first['collection_title'],'material':material,'url':first['url'],
            'new_material_position':position,'model_selection_unchanged':first['model_selection_after'],
            'original_materials_preserved':True,'verified_pages_count':349})
        print(json.dumps(summary,ensure_ascii=False),flush=True)
    finally:
        client.close()


if __name__=='__main__':
    main()
