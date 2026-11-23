include "RepoDiscoU16Frame.dfy"

module RepoDiscoFrameBatch {
  import U = StandardLibrary.UInt
  import F = RepoDiscoU16Frame
  import opened Wrappers

  datatype Batch = Batch(payloads: seq<seq<U.uint8>>, rest: seq<U.uint8>)

  predicate method HasCountedFrames(input: seq<U.uint8>, count: nat)
    decreases count
  {
    count == 0 ||
      (F.HasFrame(input) && HasCountedFrames(F.FrameRest(input), count - 1))
  }

  predicate method BoundedPayloads(payloads: seq<seq<U.uint8>>)
    decreases |payloads|
  {
    |payloads| == 0 ||
      (U.HasUint16Len(payloads[0]) && BoundedPayloads(payloads[1..]))
  }

  function method EncodeFrames(payloads: seq<seq<U.uint8>>): seq<U.uint8>
    requires BoundedPayloads(payloads)
    decreases |payloads|
  {
    if |payloads| == 0 then []
    else U.UInt16ToSeq(|payloads[0]| as U.uint16) + payloads[0] +
         EncodeFrames(payloads[1..])
  }

  function method {:opaque} ReadCountedFrames(input: seq<U.uint8>, count: nat)
    : (result: Result<Batch, string>)
    ensures result.Success? <==> HasCountedFrames(input, count)
    ensures result.Success? ==> |result.value.payloads| == count
    ensures result.Success? ==> BoundedPayloads(result.value.payloads)
    ensures result.Success? ==>
      input == EncodeFrames(result.value.payloads) + result.value.rest
    ensures result.Success? ==>
      result.value.rest == input[|EncodeFrames(result.value.payloads)|..]
    decreases count
  {
    // BEGIN REPLACEMENT
if count == 0 then
  assert HasCountedFrames(input, 0);
  assert BoundedPayloads([]);
  assert EncodeFrames([]) == [];
  Success(Batch([], input))
else
  reveal F.ReadU16Frame();
  var frameResult := F.ReadU16Frame(input);
  if frameResult.Failure? then
    assert !F.HasFrame(input);
    assert !HasCountedFrames(input, count);
    Failure(frameResult.error)
  else
    var payload := frameResult.value.payload;
    var rest := frameResult.value.rest;
    assert F.HasFrame(input);
    assert payload == F.FramePayload(input);
    assert rest == F.FrameRest(input);
    assert U.HasUint16Len(payload);
    var recursiveResult := ReadCountedFrames(rest, count - 1);
    if recursiveResult.Failure? then
      assert !HasCountedFrames(rest, count - 1);
      assert !HasCountedFrames(input, count);
      Failure(recursiveResult.error)
    else
      var subPayloads := recursiveResult.value.payloads;
      var finalRest := recursiveResult.value.rest;
      assert HasCountedFrames(rest, count - 1);
      assert HasCountedFrames(input, count);
      var payloads := [payload] + subPayloads;
      assert |payloads| == count;
      assert BoundedPayloads(subPayloads);
      assert U.HasUint16Len(payload);
      assert payloads[1..] == subPayloads;
      assert BoundedPayloads(payloads);
      assert input == U.UInt16ToSeq(|payload| as U.uint16) + payload + rest;
      assert rest == EncodeFrames(subPayloads) + finalRest;
      assert EncodeFrames(payloads) == U.UInt16ToSeq(|payloads[0]| as U.uint16) + payloads[0] + EncodeFrames(payloads[1..]);
      assert payloads[0] == payload;
      assert EncodeFrames(payloads) == U.UInt16ToSeq(|payload| as U.uint16) + payload + EncodeFrames(subPayloads);
      assert input == EncodeFrames(payloads) + finalRest;
      Success(Batch(payloads, finalRest))
    // END REPLACEMENT
  }
}
