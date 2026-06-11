#pragma once
#include <cmath>

struct Vec3 {
    double x;
    double y;
    double z;

    // Constructors
    Vec3() : x(0.0), y(0.0), z(0.0) {}
    Vec3(double x, double y, double z) : x(x), y(y), z(z) {}

    // Basic arithmetic operations
    Vec3 operator+(const Vec3& v) const { return Vec3(x + v.x, y + v.y, z + v.z); }
    Vec3 operator-(const Vec3& v) const { return Vec3(x - v.x, y - v.y, z - v.z); }
    Vec3 operator*(double s) const { return Vec3(x * s, y * s, z * s); }
    Vec3 operator/(double s) const { return Vec3(x / s, y / s, z / s); }

    // Compound assignment operators
    Vec3& operator+=(const Vec3& v) { x += v.x; y += v.y; z += v.z; return *this; }
    Vec3& operator-=(const Vec3& v) { x -= v.x; y -= v.y; z -= v.z; return *this; }
    Vec3& operator*=(double s) { x *= s; y *= s; z *= s; return *this; }
    Vec3& operator/=(double s) { x /= s; y /= s; z /= s; return *this; }

    // Vector math operations
    double dot(const Vec3& v) const { return x * v.x + y * v.y + z * v.z; }
    double squaredNorm() const { return x * x + y * y + z * z; }
    double norm() const { return std::sqrt(squaredNorm()); }

    // Returns a normalized copy of the vector
    Vec3 normalized() const {
        double n = norm();
        if (n > 0.0) {
            return *this / n;
        }
        return Vec3(0.0, 0.0, 0.0);
    }
};

// Global operator to support scalar multiplication from the left (e.g., 2.0 * vec)
inline Vec3 operator*(double s, const Vec3& v) {
    return v * s;
}