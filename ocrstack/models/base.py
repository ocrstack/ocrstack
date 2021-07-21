import torch.nn as nn
from ocrstack.config.config import Config
from ocrstack.data.collate import Batch
from ocrstack.models.conv import resnet_feature
from ocrstack.models.layers.attention import DotProductAttention

from .layers.sequence_decoder import (AttentionLSTMDecoder, BaseDecoder,
                                      TransformerDecoderAdapter)
from .layers.sequence_encoder import BaseEncoder


class ModelInterface:

    def example_inputs(self):
        pass

    def train_batch(self, batch: Batch):
        pass

    def predict(self, batch: Batch):
        pass

    
class BaseModel(nn.Module, ModelInterface):

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.backbone = self.build_backbone(cfg)
        self.encoder = self.build_encoder(cfg)
        self.decoder = self.build_decoder(cfg)

    def build_backbone(self, cfg: Config) -> nn.Module:
        cfg_node = cfg.MODEL.BACKBONE
        if cfg_node.TYPE == 'resnet18':
            backbone, _ = resnet_feature('resnet18', cfg_node.PRETRAINED)
            return backbone

        raise ValueError(f'Backbone type = {cfg_node.TYPE} is not supported')

    def build_encoder(self, cfg: Config) -> BaseEncoder:
        cfg_node = cfg.MODEL.ENCODER
        if cfg_node.TYPE == 'tf_encoder':
            return None

        raise ValueError(f'Encoder type = {cfg_node.TYPE} is not supported')

    def build_decoder(self, cfg: Config) -> BaseDecoder:
        cfg_node = cfg.MODEL.DECODER
        if cfg_node.TYPE == 'tf_decoder':
            decoder = TransformerDecoderAdapter(
                text_embedding=nn.Linear(cfg_node.VOCAB_SIZE, cfg_node.D_MODEL),
                text_classifier=nn.Linear(cfg_node.D_MODEL, cfg_node.VOCAB_SIZE),
                decoder=nn.TransformerDecoder(
                    nn.TransformerDecoderLayer(cfg_node.D_MODEL, cfg_node.NUM_HEADS),
                    cfg_node.NUM_LAYERS
                ),
            )
            return decoder
        elif cfg_node.TYPE == 'attn_lstm':
            decoder = AttentionLSTMDecoder(
                text_embedding=nn.Linear(cfg_node.VOCAB_SIZE, cfg_node.HIDDEN_SIZE),
                text_classifier=nn.Linear(cfg_node.HIDDEN_SIZE, cfg_node.VOCAB_SIZE),
                lstm=nn.LSTMCell(cfg_node.VOCAB_SIZE + cfg_node.HIDDEN_SIZE, cfg_node.HIDDEN_SIZE),
                attention=DotProductAttention(scaled=True),
                teacher_forcing=False,
            )
            return decoder

        raise ValueError(f'Decoder type = {cfg_node.TYPE} is not supported')

    def freeze(self):
        for param in self.parameters():
            param.requires_grad_(False)
