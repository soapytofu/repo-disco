include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Base, Direct
  export Deep provides K, Base, Finish
  import K = Kernel`Internal
  lemma Base(s: seq<int>, t: seq<int>)
    requires |s| == 0
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
  { reveal K.Total(); assert s == []; assert s + t == t; }
  lemma Direct(s: seq<int>, t: seq<int>)
    requires |s| > 0
    requires K.Total(s[1..] + t) == K.Total(s[1..]) + K.Total(t)
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
  {
    assert |s + t| > 0;
    assert (s + t)[0] == s[0];
    assert (s + t)[1..] == s[1..] + t;
    reveal K.Total();
    assert K.Total(s + t) == s[0] + K.Total(s[1..] + t);
    assert K.Total(s) == s[0] + K.Total(s[1..]);
  }
  lemma Finish(s: seq<int>, t: seq<int>)
    requires |s| > 0
    requires K.StepReady(s, t)
    ensures K.Total(s + t) == K.Total(s) + K.Total(t)
  {
    reveal K.StepReady(); reveal K.SplitReady(); reveal K.Total();
    assert K.Total(s + t) == s[0] + K.Total(s[1..] + t);
    assert K.Total(s) == s[0] + K.Total(s[1..]);
  }
}
