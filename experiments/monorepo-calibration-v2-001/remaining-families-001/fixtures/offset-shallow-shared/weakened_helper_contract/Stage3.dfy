include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Base, Direct
  export Deep provides K, Base, Finish
  import K = Kernel`Internal
  lemma Base(s: seq<int>, t: seq<int>, o: int)
    requires |s| == 0
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
  { reveal K.Score(); assert s == []; assert s+t == t; }
  lemma Direct(s: seq<int>, t: seq<int>, o: int)
    requires |s| > 0
    requires K.Score(s[1..]+t,o+1) == K.Score(s[1..],o+1) + K.Score(t,(o+1)+|s[1..]|)
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
  {
    assert |s+t| > 0;
    assert (s+t)[0] == s[0];
    assert (s+t)[1..] == s[1..]+t;
    assert (o+1)+|s[1..]| == o+|s|;
    reveal K.Score();
    assert K.Score(s+t,o) == o*s[0] + K.Score(s[1..]+t,o+1);
    assert K.Score(s,o) == o*s[0] + K.Score(s[1..],o+1);
  }
  lemma Finish(s: seq<int>, t: seq<int>, o: int)
    requires |s| > 0 && K.StepReady(s,t,o)
    ensures K.Score(s+t,o) == K.Score(s,o) + K.Score(t,o+|s|)
  {
    reveal K.StepReady(); reveal K.SplitReady(); reveal K.Score();
    assert K.Score(s+t,o) == o*s[0] + K.Score(s[1..]+t,o+1);
    assert K.Score(s,o) == o*s[0] + K.Score(s[1..],o+1);
  }
}
