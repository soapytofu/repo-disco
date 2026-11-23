// RepoDisco analyst reference. Native verification is UNKNOWN.
// Proposed additive path: StandardLibrary/src/RepoDiscoU16Frame.dfy.
// The contracts/specifications/imports are host-owned; only ReadU16Frame's body is editable.
include "UInt.dfy"
include "../../libraries/src/Wrappers.dfy"

module RepoDiscoU16Frame {
  import U = StandardLibrary.UInt
  import opened Wrappers

  datatype Frame = Frame(payload: seq<U.uint8>, rest: seq<U.uint8>)

  predicate method HasFrame(input: seq<U.uint8>) {
    2 <= |input| && 2 + (U.SeqToUInt16(input[..2]) as nat) <= |input|
  }

  function method FramePayload(input: seq<U.uint8>): seq<U.uint8>
    requires HasFrame(input)
  {
    input[2..2 + (U.SeqToUInt16(input[..2]) as nat)]
  }

  function method FrameRest(input: seq<U.uint8>): seq<U.uint8>
    requires HasFrame(input)
  {
    input[2 + (U.SeqToUInt16(input[..2]) as nat)..]
  }

  function method {:opaque} ReadU16Frame(input: seq<U.uint8>)
    : (result: Result<Frame, string>)
    ensures result.Success? <==> HasFrame(input)
    ensures result.Success? ==>
      result.value.payload == FramePayload(input) &&
      result.value.rest == FrameRest(input)
    ensures result.Success? ==> U.HasUint16Len(result.value.payload)
    ensures result.Success? ==>
      input == U.UInt16ToSeq(|result.value.payload| as U.uint16) +
               result.value.payload + result.value.rest
  {
    // BEGIN REPLACEMENT
    if |input| < 2 then
      Failure("Missing length")
    else
      var length := U.SeqToUInt16(input[..2]);
      var n := length as nat;
      if |input| < 2 + n then
        Failure("Truncated payload")
      else
        var payload := input[2..2+n];
        var rest := input[2+n..];
        assert |payload| == n;
        assert U.UInt16ToSeq(length) == input[..2];
        assert input == input[..2] + payload + rest;
        Success(Frame(payload, rest))
    // END REPLACEMENT
  }
}

