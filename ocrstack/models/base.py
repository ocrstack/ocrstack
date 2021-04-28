import torch
import torch.nn as nn
from ocrstack.data.collate import Batch
from ocrstack.opts.string_decoder import StringDecoder


class BaseModel(nn.Module):

    def freeze(self):
        for param in self.parameters():
            param.requires_grad_(False)


class TrainBridge(nn.Module):
    def __init__(self, model: BaseModel, string_decoder: nn.Module):
        super(TrainBridge, self).__init__()
        self.model = model
        self.string_decoder = string_decoder


class CTCTrainBridge(TrainBridge):

    def forward(self, batch: Batch):
        outputs = self.model(batch.images)
        if self.training:
            return outputs

        predicts, lengths = self.string_decoder(outputs)
        return predicts, lengths


class Seq2SeqTrainBridge(TrainBridge):

    def __init__(self, model, string_decoder, sos_onehot, eos_onehot, max_length):
        # type: (nn.Module, StringDecoder, torch.Tensor, torch.Tensor, int) -> None
        super(Seq2SeqTrainBridge, self).__init__(model, string_decoder)
        self.sos_onehot = sos_onehot
        self.eos_onehot = eos_onehot
        self.max_length = max_length

    def forward(self, batch: Batch):
        if self.training:
            logits = self.model(batch.images, batch.text[:, :-1].float(), batch.lengths + 1)
            return logits

        predicts, lengths = self.model.decode(batch.images,
                                              sos_onehot=self.sos_onehot,
                                              eos_onehot=self.eos_onehot,
                                              max_length=self.max_length)
        predicts, lengths = self.string_decoder(predicts, lengths)
        return predicts, lengths