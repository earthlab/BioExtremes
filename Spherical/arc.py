"""This module implements a variety of parameterized simple curves on the sphere."""

from abc import abstractmethod, ABC
import numpy as np

from Spherical import numerics
from Spherical import functions as fn


class Arc(ABC):
    """An abstract class providing the interface of an Arc on the sphere."""

    @abstractmethod
    def length(self) -> float:
        """Return the length of the Arc, in degrees."""
        pass

    def _checkt(self, t):
        """Check whether t is a valid input to the arc-length parameterization, i.e. 0 <= t <= length."""
        t = np.array(t)
        if (t > self.length()).any():
            raise fn.SphericalGeometryException("Arc-length parameterization does not admit parameters t > length")
        if (t < 0).any():
            raise fn.SphericalGeometryException("Arc-length parameterization does not admit parameters t < 0")

    @abstractmethod
    def _uncheckedxyz(self, t: np.ndarray) -> np.ndarray:
        """xyz(t) without checking t"""

    def xyz(self, t: float | np.ndarray) -> np.ndarray:
        """
        Unit-speed parameterization of the Arc's Cartesian coordinates in degrees.

        :param t: shape (,) or (n,)
        :return: x,y,z coordinates of parameterization, shape (3,) or (3, n)
        """
        self._checkt(t)
        s = np.atleast_1d(t).astype(float)
        result = self._uncheckedxyz(s)
        if not np.array(t).shape:
            result = result.reshape(-1)
        return result

    def __call__(self, t: float | np.ndarray) -> np.ndarray:
        """
        Unit-speed parameterization of the Arc's spherical coordinates in degrees.

        :param t: shape (,) or (n,)
        :return: lat, lon coordinates of parameterization, shape (2,) or (2, n)
        """
        xyzt = self.xyz(t)
        return fn.xyz2latlon(xyzt)

    @abstractmethod
    def _intersections(self, other, atol: float) -> np.ndarray:
        """
        Called by public method with the same name. Raises a SphericalGeometryException if other is an unrecognized
        implementation of Arc.

        :type other: Arc
        :param other: Another Arc to intersect.
        :param atol: Error tolerance, in degrees.
        :return: The array of intersections, with shape (2, n), or None if no intersections occur.
        """

    def intersections(self, other, atol: float = numerics.default_tol) -> np.ndarray:
        """
        Return a numpy array of the (lat, lon) points at which this arc intersects another, up to a tolerance.
        Note that this array may be empty, and will omit infinitely many points of intersection wherever the two arcs
        coincide.

        :type other: Arc
        :param other: Another Arc to intersect.
        :param atol: Error tolerance, in degrees.
        :return: The array of intersections, with shape (2, n), or None if no intersections occur.
        """
        # TODO: Exceptions shouldn't be raised unless something is WRONG--make it work differently
        try:
            return self._intersections(other, atol)
        except fn.SphericalGeometryException:
            return other._intersections(self, atol)

    def nearest(self, point: tuple | np.ndarray, atol: float = numerics.default_tol) -> tuple:
        """
        Greedy nearest-point calculation, using golden section search, which works for a Geodesic or part of a
        Parallel, but may need to be overridden for sophisticated Arcs.

        :param point: query point (lat, lon)
        :param atol: error tolerance
        :return: t, d, where t is the parameter value of the nearest point, and d is the distance in radii to the
                    nearest point.
        """
        xyz = fn.latlon2xyz(point)

        def distance(t):
            xyzt = self.xyz(t)
            return fn.anglexyz(xyz, xyzt)

        return numerics.goldensection(distance, a=0, b=self._angle, atol=atol)


class Geodesic(Arc):
    """An Arc representing the shortest path between two points."""

    def __init__(self, source: tuple | np.ndarray, dest: tuple | np.ndarray, warn=True):
        """
        Construct a Geodesic shortest path.

        :param source: start of path
        :param dest: end of path
        :param warn: causes SphericalGeometryException if source and dest are antipodal, in which case the shortest
                        path is not unique, and intersections computed with the Geodesic will be untrustworthy.
        """
        self._xyz0 = fn.latlon2xyz(source)
        self._xyz1 = fn.latlon2xyz(dest)
        self._angle = fn.anglexyz(self._xyz0, self._xyz1)
        if warn and self._angle >= 180 - numerics.default_tol:
            raise fn.SphericalGeometryException("Geodesics defined by near-antipodal points are numerically unstable.")
        self._axis = np.cross(self._xyz0, self._xyz1)
        if (self._axis == 0).all():
            # axis and orthonormal are arbitrary in this case
            self._axis = np.array([1, 0, 0])
            self._orthonormal = np.array([0, 1, 1])
        else:
            self._axis /= np.linalg.norm(self._axis)
            self._orthonormal = np.cross(self._axis, self._xyz0)
            self._orthonormal /= np.linalg.norm(self._orthonormal)

    def length(self) -> float:
        return self._angle

    def _uncheckedxyz(self, t: np.ndarray) -> np.ndarray:
        return np.outer(self._xyz0, fn.cosd(t)) + np.outer(self._orthonormal, fn.sind(t))

    def _intersectsgc(self, gc, atol: float) -> np.ndarray | None:
        """
        Return where this geodesic intersects the great circle containing another geodesic gc.

        :type gc: Geodesic
        """
        d0 = gc._axis @ self._xyz0
        d1 = gc._axis @ self._xyz1
        if d0 * d1 <= 0.5 * atol:
            inplane = d0 * self._xyz1 - d1 * self._xyz0
            inplane *= inplane @ (self._xyz0 + self._xyz1)
            return fn.xyz2latlon(inplane)

    def _intersections(self, other, atol: float = numerics.default_tol) -> np.ndarray:
        if isinstance(other, Geodesic):
            p0 = self._intersectsgc(other, atol)
            if p0 is None:
                return
            p1 = other._intersectsgc(self, atol)
            if p1 is None:
                return
            geo = Geodesic(p0, p1, warn=False)
            dist = geo.length()
            if dist < atol:
                return np.array([geo(dist / 2)]).T     # return midpoint of path between intersections
            return
        raise fn.SphericalGeometryException(f"Cannot compute intersections between Geodesic and {type(other)}")


class Parallel(Arc):
    """Part of a latitude line."""

    def __init__(self, lat: float, lon0: float, lon1: float, crossdl: bool = False):
        """
        Construct a Parallel.

        :param lat: latitude
        :param lon0: starting longitude
        :param lon1: ending longitude
        :param crossdl: whether to cross the International Date Line, False by default
        """
        self._lat = lat
        self._lon0 = lon0
        self._lon1 = lon1
        self._crossdl = crossdl
        self._dlon = lon1 - lon0
        self._dsdlon = fn.cosd(lat) * np.sign(self._dlon)    # signed equatorial degrees per signed degree longitude
        self._lonrange = (min(lon0, lon1), max(lon0, lon1))
        if crossdl:
            self._dlon = -np.sign(self._dlon) * (360 - np.abs(self._dlon))
            self._lonrange = (max(lon0, lon1), min(lon0, lon1))
        self._len = np.abs(self._dsdlon * self._dlon)

    def length(self) -> float:
        return self._len

    # override inherited call method because here it is more natural to work in spherical coordinates
    def __call__(self, t: float | np.ndarray) -> np.ndarray:
        """
        Unit-speed parameterization of the Parallel's spherical coordinates in (equatorial) degrees. This means that
        longitude changes at a speed of cosine(latitude).

        :param t: shape (,) or (n,)
        :return: lat, lon coordinates of parameterization, shape (2,) or (2, n)
        """
        self._checkt(t)
        lon = (self._lon0 + t * self._dsdlon + 180) % 360 - 180
        lat = self._lat * np.ones_like(lon)
        return np.array([lat, lon])

    def _uncheckedxyz(self, t: np.ndarray) -> np.ndarray:
        return fn.latlon2xyz(self(t))

    def _inlonrange(self, lon) -> bool:
        """Return whether a longitude value lies in the range of this Parallel."""
        a, b = self._lonrange
        if self._crossdl:
            return lon >= a or lon <= b
        return a <= lon <= b

    def _intersections(self, other, atol: float) -> np.ndarray:
        if isinstance(other, Parallel):
            if self._lat == other._lat:
                a, b = self._lonrange
                mn = min(other._lon0, other._lon1)
                mx = max(other._lon0, other._lon1)
                ints = []
                if self._crossdl:
                    if mn <= a:
                        ints.append(np.array([self._lat, mn]))
                    if mx >= b:
                        ints.append(np.array([self._lat, mx]))
                else:
                    if a <= mn <= b:
                        ints.append(np.array([self._lat, mn]))
                    if a <= mx <= b:
                        ints.append(np.array([self._lat, mx]))
                if -a == mx == 180 or b == -mn == 180:
                    ints.append(np.array([self._lat, -180]))
                ints = np.array(ints)
                ints[:, 1] = (ints[:, 1] + 180) % 360 - 180
                ints = np.unique(ints, axis=0).T
                if ints.shape[0]:
                    return ints
            return
        if isinstance(other, Geodesic):
            sgn = np.sign(self._lat)
            minimize = lambda s: -sgn * other(s)[0]
            findroot = lambda s: other(s)[0] - self._lat
            t_split, extreme = numerics.goldensection(minimize, a=0, b=other.length(), atol=atol)
            latstart, latextreme, latend = other(np.array([0, t_split, other.length()]))[0]
            ints = []
            if latstart <= self._lat <= latextreme or latextreme <= self._lat <= latstart:
                t1 = numerics.bisection(findroot, a=0, b=t_split, atol=atol)
                lat, lon = other(t1)
                if self._inlonrange(lon):
                    ints.append((lat, lon))
            if latend < self._lat < latextreme or latextreme < self._lat < latend:      # strict < helps at equator
                t2 = numerics.bisection(findroot, a=t_split, b=other.length(), atol=atol)
                lat, lon = other(t2)
                if self._inlonrange(lon):
                    ints.append((lat, lon))
            ints = np.unique(ints, axis=0).T
            if ints.shape[0]:
                return ints
            return
        raise fn.SphericalGeometryException(f"Cannot compute intersection between Parallel and {type(other)}")


class SimplePiecewiseArc(Arc):
    """A continuous simple curve consisting of Arc segments."""

    def __init__(
            self,
            arcs: list[Arc],
            atol: float = numerics.default_tol,
            checksimple: bool = True,
            checkcontinuous: bool = True
            ):
        """
        Initiate a SimplePiecewiseArc from a list of Arcs.

        :param arcs: List of Arcs, each of which starts at the end of the previous.
        :param atol: Continuity is enforced up to this tolerance, in degrees.
        :param checksimple: whether to enforce that the curve is simple.
        :param checkcontinuous: whether to enforce that the curve is continuous.
        """
        self._arcs = arcs
        self._atol = atol
        self._sublen = np.array([
            sum([arc.length() for arc in arcs[:i]])
            for i in range(len(arcs))
        ])
        if np.unique(self._sublen).shape != self._sublen.shape:
            raise fn.SphericalGeometryException("SimplePiecewiseArc may not include length-zero Arcs.")
        self._len = self._sublen[-1] + arcs[-1].length()

        # determine closedness
        arc1 = self._arcs[0]
        arcn = self._arcs[-1]
        dist = fn.anglelatlon(arcn(arcn.length()), arc1(0))
        self._closed = dist < self._atol

        # is this a valid simple curve?
        if checkcontinuous:
            self.checkcontinuity()
        if checksimple:
            self.checksimplicity()

        # establish reference p for containment queries
        self._refpt = (0.0001234, -0.0004321)   # hopefully doesn't lie on a great circle containing one of self._arcs!
        self._refinside = self.contains(self._refpt, method='angles')

    def checkcontinuity(self):
        """Raise an exception if this curve is not continuous."""
        for arc1, arc2 in zip(self._arcs[:-1], self._arcs[1:]):
            err = fn.anglelatlon(arc1(arc1.length()), arc2(0))
            if err > self._atol:
                raise fn.SphericalGeometryException(
                    f"SimplePiecewiseArc is discontinuous at seam with tolerace {self._atol}.")

    def checksimplicity(self):
        """Raise an exception if this is not a simple curve, i.e. it intersects itself."""
        for i in range(len(self._arcs)):
            for j in range(i):
                ints = self._arcs[i].intersections(self._arcs[j], atol=self._atol)
                if ints is not None:
                    if j == i - 1 and ints.shape[1] == 1:       # allowed to intersect end of previous arc
                        continue
                    if j == 0 and i == len(self._arcs) - 1 and ints.shape[1] == 1 and self.isclosed():
                        continue
                    raise fn.SphericalGeometryException(f"SimplePiecewiseArc crosses itself with tolerance {self._atol}.")

    def isclosed(self) -> bool:
        """Return whether the curve is closed."""
        return self._closed

    def contains(self, point: tuple | np.ndarray, method: str = 'refpt') -> bool:
        """
        Return whether a (lat, lon) point is inside the curve. Assumes counterclockwise orientation. If method='refpt',
        the default, then containment is determined by counting the intersections between the Arc and a Geodesic
        connecting the queried p to a reference p. If method='angles', then containment is determined by
        comparing angles between the shortest path to the Arc and the counterclockwise and clockwise tangents.
        The 'refpt' method is faster, but fails in some probability-zero cases, e.g. if the query point is coplanar
        with a Geodesic side of the closed curve.
        """
        if not self.isclosed():
            raise fn.SphericalGeometryException("Containment check for a non-closed curve.")
        if method == 'angles':
            return self.distance(point) == 0.
        if method != 'refpt':
            raise ValueError(f"Invalid method for containment check: {method}")
        path = Geodesic(point, self._refpt, warn=False)
        if path.length() >= 180 - self._atol:     # break long geodesic in parts for accurate intersections
            path = SimplePiecewiseArc([
                Geodesic(path(0), path(90)),
                Geodesic(path(90), path(path.length()))
            ])
        ints = self.intersections(path, self._atol)
        nints = 0 if ints is None else ints.shape[1]
        return bool((nints + self._refinside) % 2)

    def distance(self, p: tuple | np.ndarray) -> float:
        """
        Return the distance from a point to the region enclosed by the curve, accurate within absolute tolerance.
        Unlike nearest(), this method returns a distance of 0 for any point inside the curve. Whether the point is
        inside is determined using angle comparison.
        """
        t, d = self.nearest(p)
        if d < self._atol:
            return 0.                                           # include boundary of closed shape
        q = self(t)                                             # nearest point on boundary
        qp = Geodesic(q, p)
        q = fn.latlon2xyz(q)
        n = qp.xyz(self._atol) - q                              # normal at q in direction of p
        dt = min(self._atol, 0.4 * self._len)
        tf = (t + dt) % self._len
        f = self.xyz(tf) - q                                    # forward tangent at q
        tb = (t - dt) % self._len
        b = self.xyz(tb) - q                                    # backward tangent at q
        if np.cross(n, f) @ q <= np.cross(n, b) @ q:
            return 0.
        return d

    """Implement abstract methods of base class Arc"""

    def length(self) -> float:
        return self._len

    # TODO: really ought to override __call__() to avoid converting in and out of xyz for Parallels
    def _uncheckedxyz(self, t: np.ndarray) -> np.ndarray:
        compare = np.subtract.outer(t, self._sublen) >= 0
        idx = compare.sum(axis=1) - 1
        t -= self._sublen[idx]
        result = np.empty((3, t.shape[0]))
        for i in range(len(self._arcs)):
            where_i = np.argwhere(idx == i)[:, 0]
            ti = t[where_i]
            ti[ti < 0] = 0  # round off numerical errors outside allowed range
            ti[ti > self._arcs[i].length()] = self._arcs[i].length()
            result[:, where_i] = self._arcs[i]._uncheckedxyz(ti)
        return result

    def _intersections(self, other, atol: float = numerics.default_tol) -> np.ndarray:
        ints = [arc.intersections(other, atol) for arc in self._arcs]
        ints = np.unique([i for i in ints if i is not None], axis=0)
        if ints.shape[0]:
            return np.hstack(ints)

    # TODO: override decorator?
    def nearest(self, point: tuple | np.ndarray, atol: float = numerics.default_tol) -> tuple:
        """
        Nearest-point calculation involves calling nearest() method of each constituent Arc. Overridden from base
        class Arc.

        :param point: query point (lat, lon)
        :param atol: error tolerance
        :return: t, d, where t is the parameter value of the nearest point, and d is the distance in radii to the
                    nearest point.
        """
        td = np.array([arc.nearest(point, atol) for arc in self._arcs])
        t = td[:, 0] + self._sublen
        d = td[:, 1]
        idx = np.argmin(d)
        return t[idx], d[idx]


class Polygon(SimplePiecewiseArc):
    """The counterclockwise-oriented boundary of a spherical polygon."""

    def __init__(self, points: np.array, **kwargs):
        """
        Construct a Polygon from a counterclockwise-ordered sequence of (lat, lon) points with shape (2, n).
        Keyword arguments passed to SimplePiecewiseArc.__init__()
        """
        verts = points.T
        sides = [Geodesic(p0, p1) for p0, p1 in zip(verts[:-1], verts[1:])]
        sides.append(Geodesic(verts[-1], verts[0]))
        super().__init__(sides, **kwargs)


class BoundingBox(SimplePiecewiseArc):
    """A lat/lon bounding box on the sphere."""

    def __init__(self, topleft: tuple, bottomright: tuple):
        """
        Create a bounding box from its two corners.

        :param topleft: (lat, lon) northwest corner
        :param bottomright: (lat, lon) southeast corner
        """
        self._maxlat, self._minlon = topleft
        self._minlat, self._maxlon = bottomright
        self._crossdl = self._minlon > self._maxlon
        super().__init__([                                          # counterclockwise orientation
            Geodesic(topleft, (self._minlat, self._minlon)),
            Parallel(self._minlat, lon0=self._minlon, lon1=self._maxlon, crossdl=self._crossdl),
            Geodesic(bottomright, (self._maxlat, self._maxlon)),
            Parallel(self._maxlat, lon0=self._maxlon, lon1=self._minlon, crossdl=self._crossdl)
        ])

    def contains(self, point: tuple, method="gets ignored") -> bool:
        """Returns whether a (lat, lon) point is inside the BoundingBox. Overrides SimplePiecewiseArc.contains()."""
        lat, lon = point
        if not self._minlat <= lat <= self._maxlat:
            return False
        if self._minlon <= lon <= self._maxlon:
            return not self._crossdl
        return self._crossdl


