"""Real and complex elements with built-in truncation. """

from sympy.polys.domains.domainelement import DomainElement

from sympy.mpmath.ctx_mp_python import PythonMPContext, _mpf, _mpc, _constant
from sympy.mpmath.libmp import (MPZ_ONE, fzero, fone, finf, fninf, fnan,
    round_nearest, mpf_mul, mpf_abs, mpf_lt, mpc_abs, repr_dps, int_types,
    from_int, from_float, from_str, to_rational)
from sympy.mpmath.rational import mpq

class RealElement(_mpf, DomainElement):
    """An element of a real domain. """

    __slots__ = ['__mpf__']

    def _set_mpf(self, val):
        prec, rounding = self.context._prec_rounding
        tol = self.context.tol

        if mpf_lt(mpf_abs(val, prec, rounding), tol):
            self.__mpf__ = fzero
        else:
            self.__mpf__ = val

    _mpf_ = property(lambda self: self.__mpf__, _set_mpf)

    def parent(self):
        return self.context._parent

class ComplexElement(_mpc, DomainElement):
    """An element of a complex domain. """

    __slots__ = ['__mpc__']

    def _set_mpc(self, val):
        prec, rounding = self.context._prec_rounding
        tol = self.context.tol

        # norm = mpc_abs(val, prec, rounding)
        # tol = mpf_max(tol, mpf_mul(norm, tol))

        re, im = val

        if mpf_lt(mpf_abs(re, prec, rounding), tol):
            re = fzero
        if mpf_lt(mpf_abs(im, prec, rounding), tol):
            im = fzero

        self.__mpc__ = (re, im)

    _mpc_ = property(lambda self: self.__mpc__, _set_mpc)

    def parent(self):
        return self.context._parent

new = object.__new__

class MPContext(PythonMPContext):

    def __init__(ctx, prec=53, dps=None, tol=None):
        ctx._prec_rounding = [prec, round_nearest]

        if dps is None:
            ctx._set_prec(prec)
        else:
            ctx._set_dps(dps)

        ctx.mpf = type('RealElement', (RealElement,), {})
        ctx.mpc = type('ComplexElement', (ComplexElement,), {})
        ctx.mpf._ctxdata = [ctx.mpf, new, ctx._prec_rounding]
        ctx.mpc._ctxdata = [ctx.mpc, new, ctx._prec_rounding]
        ctx.mpf.context = ctx
        ctx.mpc.context = ctx
        ctx.constant = type('constant', (_constant,), {})
        ctx.constant._ctxdata = [ctx.mpf, new, ctx._prec_rounding]
        ctx.constant.context = ctx

        ctx.types = [ctx.mpf, ctx.mpc, ctx.constant]
        ctx.trap_complex = True
        ctx.pretty = True

        if tol is None:
            hundred = (0, 25, 2, 5)
            eps = (0, MPZ_ONE, 1-ctx.prec, 1)
            ctx.tol = mpf_mul(hundred, eps)
        else:
            ctx.tol = ctx._convert_tol(tol)

        ctx.tolerance = ctx.make_mpf(ctx.tol)
        ctx.max_denom = int(1/ctx.tolerance)

        ctx.zero = ctx.make_mpf(fzero)
        ctx.one = ctx.make_mpf(fone)
        ctx.j = ctx.make_mpc((fzero, fone))
        ctx.inf = ctx.make_mpf(finf)
        ctx.ninf = ctx.make_mpf(fninf)
        ctx.nan = ctx.make_mpf(fnan)

    def _convert_tol(ctx, tol):
        if isinstance(tol, int_types):
            return from_int(tol)
        if isinstance(tol, float):
            return from_float(tol)
        prec, rounding = ctx._prec_rounding
        if isinstance(tol, basestring):
            return from_str(tol, prec, rounding)
        raise ValueError("expected a real number, got %s" % tol)

    def _convert_fallback(ctx, x, strings):
        raise TypeError("cannot create mpf from " + repr(x))

    @property
    def _repr_digits(ctx):
        return repr_dps(ctx._prec)

    @property
    def _str_digits(ctx):
        return ctx._dps

    def to_rational(ctx, s, limit=True):
        p, q = to_rational(s._mpf_)

        if not limit or q <= ctx.max_denom:
            return p, q

        p0, q0, p1, q1 = 0, 1, 1, 0
        n, d = p, q

        while True:
            a = n//d
            q2 = q0 + a*q1
            if q2 > ctx.max_denom:
                break
            p0, q0, p1, q1 = p1, q1, p0 + a*p1, q2
            n, d = d, n - a*d

        k = (ctx.max_denom - q0)//q1

        number = mpq(p, q)
        bound1 = mpq(p0 + k*p1, q0 + k*q1)
        bound2 = mpq(p1, q1)

        if not bound2 or not bound1:
            return p, q
        elif abs(bound2 - number) <= abs(bound1 - number):
            return bound2._mpq_
        else:
            return bound1._mpq_

    def almosteq(ctx, s, t, rel_eps=None, abs_eps=None):
        t = ctx.convert(t)
        if abs_eps is None and rel_eps is None:
            rel_eps = abs_eps = ctx.tolerance
        if abs_eps is None:
            abs_eps = rel_eps
        elif rel_eps is None:
            rel_eps = abs_eps
        diff = abs(s-t)
        if diff <= abs_eps:
            return True
        abss = abs(s)
        abst = abs(t)
        if abss < abst:
            err = diff/abst
        else:
            err = diff/abss
        return err <= rel_eps