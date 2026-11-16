"""Frozen 2.2 inference. Approved VALIDATION replay, saved TEST metrics only."""
from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from .structure import ROOT
from .inference import InferenceError, verified, snapshot_hash, strict_request
from .inference import validate_request as legacy_validate_request, VERSION as LEGACY_VERSION
from .data_v2_2 import load_records
from .preprocessing_train_v2_2 import AuthorizedPreprocessor22
from .preprocessing import validate_frame
from .final_evaluation_v2_2 import read_selection, load_model, BUILD, SELECTION, FINAL
from .validate_build import cutoff

VERSION='v2-inference-2.2-1'
SELECTION_SHA256='7d9f49856b44703021f57fc83f9d763d5d787c428b3d4dedcddac6955babff23'
RESULT_SHA256='3a5f4b87c158b49eb447bc37cbf4a541e7b046ef69559e73e3c3c9a42143e283'


def validate_request(request):
    if type(request) is not dict or request.get('contractVersion')!=VERSION:raise InferenceError('INVALID_INPUT')
    legacy_validate_request({**request,'contractVersion':LEGACY_VERSION})


class FrozenDemandInference:
    def __init__(self,root=ROOT):
        self.root=Path(root).resolve()
        verified(self.root/SELECTION,SELECTION_SHA256)
        self.selection,_=read_selection(self.root)
        self.evaluation=json.loads(verified(self.root/FINAL/'result.json',RESULT_SHA256))
        if self.evaluation['artifact_sha256']!=self.selection['artifact_sha256'] or self.evaluation['selection_sha256']!=SELECTION_SHA256:raise InferenceError('INCOMPATIBLE_ARTIFACT')
        self.catalog=json.loads(verified(self.root/BUILD/'catalog_reference.json',self.selection['input_hashes'][BUILD+'/catalog_reference.json']))
        with patch.object(AuthorizedPreprocessor22,'fit',side_effect=AssertionError('Inference forbids fit')),patch.object(RandomForestRegressor,'fit',side_effect=AssertionError('Inference forbids fit')):
            self.model=load_model(self.root,self.selection)
        self._features,rows=load_records('VALIDATION',root=self.root)
        self._fields=self.model.named_steps['preprocessing'].to_state()['state']['field_specs']
        self._metadata={}
        for r in rows:
            key=(r['productId'],r['locationId'],r['mes_objetivo'])
            if r['quality_status']!='TRAINABLE':raise InferenceError('UNAVAILABLE_REQUIRED_FEATURE')
            self._metadata[key]=dict(snapshot=r['history_snapshot_id'],cutoff=r['feature_cutoff_at'])
        self._fingerprints={k:snapshot_hash(self._features.iloc[i],k,self._metadata[k]) for i,k in enumerate(self._features.index)}

    def request_for(self,product_id,location_id,month):
        meta=self._metadata.get((product_id,location_id,month))
        if meta is None:raise InferenceError('UNAVAILABLE_REQUIRED_FEATURE')
        return dict(contractVersion=VERSION,productId=product_id,locationId=location_id,targetMonth=month,historySnapshotId=meta['snapshot'])

    def predict(self,request):
        validate_request(request)
        verified(self.root/SELECTION,SELECTION_SHA256)
        verified(self.root/self.selection['artifact'],self.selection['artifact_sha256'])
        state=self.model.named_steps['preprocessing'].to_state()
        if state['sha256']!=self.selection['preprocessing_state_sha256'] or self.model.named_steps['model'].get_params()!=self.selection['regressor_parameters']:raise InferenceError('INCOMPATIBLE_ARTIFACT')
        key=(request['productId'],request['locationId'],request['targetMonth'])
        if key[0] not in self.catalog['included_product_ids'] or key[1] not in {r['id'] for r in self.catalog['locations'] if r['type']=='TIENDA'}:raise InferenceError('UNKNOWN_ENTITY')
        meta=self._metadata.get(key)
        if meta is None:raise InferenceError('UNAVAILABLE_REQUIRED_FEATURE')
        if meta['snapshot']!=request['historySnapshotId']:raise InferenceError('SNAPSHOT_MISMATCH')
        frame=self._features.loc[[key]].copy(deep=True);fingerprint=snapshot_hash(frame.iloc[0],key,meta)
        if fingerprint!=self._fingerprints[key]:raise InferenceError('UNAVAILABLE_REQUIRED_FEATURE')
        validate_frame(frame,self._fields)
        with patch.object(AuthorizedPreprocessor22,'fit',side_effect=AssertionError('No fit')),patch.object(RandomForestRegressor,'fit',side_effect=AssertionError('No fit')),patch.object(StandardScaler,'fit',side_effect=AssertionError('No fit')):
            raw=np.asarray(self.model.predict(frame),dtype=float)
        if state!=self.model.named_steps['preprocessing'].to_state():raise InferenceError('INCOMPATIBLE_ARTIFACT')
        if raw.shape!=(1,) or not np.isfinite(raw).all():raise InferenceError('MODEL_UNAVAILABLE')
        value=float(raw[0]);s=self.selection
        warnings=['DATOS_SINTETICOS_NO_VALIDA_VENTAS_REALES','NO_REPOSICION_AUTOMATICA','PEDIDOS_EXTRAORDINARIOS_NO_INCLUIDOS','TRECE_PRODUCTOS_EMPEORAN_EN_VALIDATION']
        if value<0:warnings.append('NEGATIVE_PREDICTION_CLIPPED')
        return dict(status='OK',contractVersion=VERSION,productId=key[0],locationId=key[1],targetMonth=key[2],
            issuedAt=datetime.now(timezone.utc).isoformat(),historyCutoff=meta['cutoff'],horizonMonths=1,prediction=max(value,0),
            modelVersion=s['selection_id'],datasetVersion='2.2.0',buildId=s['build_id'],historySnapshotId=meta['snapshot'],
            origin='SYNTHETIC',mode='ACADEMIC_REPLAY',selectionId=s['selection_id'],artifactSha256=s['artifact_sha256'],
            featureSnapshotSha256=fingerprint,policyVersion=s['prediction_policy']['version'],warnings=warnings,
            evaluationContext=dict(origin='SYNTHETIC',split='TEST',**{k:self.evaluation['model_metrics'][k] for k in ['mae','rmse','r2']}))
