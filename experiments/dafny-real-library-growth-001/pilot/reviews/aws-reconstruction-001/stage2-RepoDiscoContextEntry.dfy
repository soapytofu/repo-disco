// RepoDisco analyst reference. Native verification is UNKNOWN.
// Proposed additive path:
// AwsCryptographicMaterialProviders/dafny/AwsCryptographicMaterialProviders/src/RepoDiscoContextEntry.dfy.
// This reads one key/value entry, not the pair count or a complete canonical context.
// The fixed specification allows empty UTF8 keys and values.
include "../Model/AwsCryptographyMaterialProvidersTypes.dfy"
include "../../../../StandardLibrary/src/RepoDiscoU16Frame.dfy"

module RepoDiscoContextEntry {
  import U = StandardLibrary.UInt
  import F = RepoDiscoU16Frame
  import Types = AwsCryptographyMaterialProvidersTypes
  import UTF8
  import opened Wrappers

  datatype Entry = Entry(context: Types.EncryptionContext, rest: seq<U.uint8>)

  predicate method HasContextEntry(input: seq<U.uint8>) {
    F.HasFrame(input) &&
    F.HasFrame(F.FrameRest(input)) &&
    UTF8.ValidUTF8Seq(F.FramePayload(input)) &&
    UTF8.ValidUTF8Seq(F.FramePayload(F.FrameRest(input)))
  }

  function method {:opaque} ReadContextEntry(input: seq<U.uint8>)
    : (result: Result<Entry, string>)
    ensures result.Success? <==> HasContextEntry(input)
    ensures result.Success? ==>
      result.value.context ==
        map[F.FramePayload(input) := F.FramePayload(F.FrameRest(input))]
    ensures result.Success? ==> |result.value.context| == 1
    ensures result.Success? ==> result.value.rest == F.FrameRest(F.FrameRest(input))
  {
    // BEGIN REPLACEMENT
    var keyFrame := F.ReadU16Frame(input);
    if keyFrame.Failure? then
      Failure(keyFrame.error)
    else
      var valueFrame := F.ReadU16Frame(keyFrame.value.rest);
      if valueFrame.Failure? then
        Failure(valueFrame.error)
      else if !UTF8.ValidUTF8Seq(keyFrame.value.payload) ||
              !UTF8.ValidUTF8Seq(valueFrame.value.payload) then
        Failure("Invalid UTF8")
      else
        var key: Types.Utf8Bytes := keyFrame.value.payload;
        var value: Types.Utf8Bytes := valueFrame.value.payload;
        Success(Entry(map[key := value], valueFrame.value.rest))
    // END REPLACEMENT
  }
}

