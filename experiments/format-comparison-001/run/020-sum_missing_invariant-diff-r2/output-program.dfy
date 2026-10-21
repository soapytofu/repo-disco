method SumToN(n: nat) returns (s: nat)
  ensures 2 * s == n * (n + 1)
{
  s := 0;
  var i: nat := 0;
  while i < n
    invariant i <= n
invariant 2 * s == i * (i + 1)
    decreases n - i
  {
    i := i + 1;
    s := s + i;
  }
}
