
from engine.cross_asset import CROSS_ASSET_MAP

def market_impact(regime):

    return CROSS_ASSET_MAP.get(regime, {})

