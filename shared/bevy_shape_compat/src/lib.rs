//! Compatibility shim for `bevy_shape` 0.20, whose `bounding` module is private.
//!
//! Everything `bevy_shape` exports is re-exported as is, and the old path
//! `bevy_shape::bounding::Aabb3d` keeps working through the `bounding` module below.

pub use bevy_shape::*;

pub mod bounding {
    pub use bevy_shape::Aabb3d;
}
