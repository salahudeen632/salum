import paramak
import openmc
import os
import openmc_dagmc_wrapper as odw
import openmc_plasma_source as ops
import openmc_tally_unit_converter as otuc
rotated_circle = paramak.ExtrudeCircleShape(
    points=[(0, 0),], radius=0.95, distance=1.2, workplane="XZ", name="part0.stl",
)

grey_part = paramak.ExtrudeStraightShape(
    points=[
        (-1.15, -1.25),
        (1.15, -1.25),
        (1.15, 1.75),
        (-1.15, 1.75),
    ],
    distance=1.2,
    color=(0.5, 0.5, 0.5),
    cut=rotated_circle,
    name="grey_part",
)

red_part = paramak.RotateStraightShape(
    points=[
        (0.75, -0.6),
        (0.95, -0.6),
        (0.95, 0.6),
        (0.75, 0.6),
    ],
    color=(0.5, 0, 0),
    workplane="XY",
    rotation_angle=360,
    name="red_part",
)

blue_part = paramak.RotateStraightShape(
    points=[
        (0.6, -0.6),
        (0.75, -0.6),
        (0.75, 0.6),
        (0.6, 0.6),
    ],
    color=(0, 0, 0.5),
    workplane="XY",
    rotation_angle=360,
    name="blue_part",
)

my_reactor = paramak.Reactor([grey_part, red_part, blue_part])


# exports the reactor shapes as a DAGMC h5m file which can be used as
# we will need to decrease the mesh size on this function to make the geometry better
my_reactor.export_dagmc_h5m("dagmc.h5m", min_mesh_size=1, max_mesh_size=2)

# we can open the vtk in paraview to have a look at the geometry
os.system("mbconvert dagmc.h5m dagmc.vtk")
w = openmc.Material(name="w")
w.add_element("W", 1)
w.set_density("g/cc", 19.3)

zirconium = openmc.Material(name="zirconium")
zirconium.add_element("zirconium", 1)
zirconium.set_density("g/cc", 6.6)

cr = openmc.Material(name="copper")
cr.add_element("copper", 1)
cr.set_density("g/cc", 8.96)

cu = openmc.Material(name="cu")
cu.add_element("Cr", 0.012)
cu.add_element("zirconium", 0.0007)
cu.set_density("g/cc", 8.96)

copper = openmc.Material(name="copper")
copper.add_element("copper", 1)
copper.set_density("g/cc", 8.96)
geometry = odw.Geometry(h5m_filename="dagmc.h5m")
geometry.create_sphere_of_vacuum_surface

my_source = openmc.Source()

# sets the location of the source to x=0 y=0 z=0
my_source.space = openmc.stats.Point((0, 0, 5))

# sets the direction to isotropic
my_source.angle = openmc.stats.Isotropic()

# sets the energy distribution to 100% 14MeV neutrons
my_source.energy = openmc.stats.Discrete([14e6], [1])


# this links the material tags in the dagmc h5m file with materials.
# these materials are input as strings so they will be looked up in the
# neutronics material maker package
materials = odw.Materials(
    h5m_filename=geometry.h5m_filename,
    correspondence_dict={
        "mat_blue_part": zirconium,
        "mat_grey_part": w,
        "mat_red_part": copper,
    },
)

# gets the corners of the geometry for use later
bounding_box = geometry.corners()

tally1 = odw.MeshTally3D(
    mesh_resolution=(25, 5, 25),
    bounding_box=bounding_box,  # consider using original bounding box in stead of automatic one [(-1.15,-0.6,-1.25),(1.15,0.6,1.75)]
    tally_type="heating",
)
tally2 = odw.MeshTally3D(
    mesh_resolution=(25, 5, 25),
    bounding_box=bounding_box,  # consider using original bounding box in stead of automatic one [(-1.15,-0.6,-1.25),(1.15,0.6,1.75)]
    tally_type="neutron_effective_dose",
)

# TODO add 2d and 3d tallies for (n,Xt)','heating','damage-energy'

tallies = openmc.Tallies([tally1,tally2])

settings = odw.FusionSettings()
settings.batches = 500
settings.particles = 100_00
settings.source = my_source
my_model = openmc.Model(
    materials=materials, geometry=geometry, settings=settings, tallies=tallies
)

# starts the simulation
statepoint_file = my_model.run()

print(f"neutronics results are saved in {statepoint_file}")
# create vtk of 3d heating tally

from openmc_mesh_tally_to_vtk import write_mesh_tally_to_vtk
import openmc

# assumes you have a statepoint file from the OpenMC simulation
statepoint = openmc.StatePoint(f'statepoint.{settings.batches}.h5')

statepoint.tallies

# assumes the statepoint file has a RegularMesh tally with a certain name
my_tally = statepoint.get_tally(name='heating_on_3D_mesh')
my_tally1=statepoint.get_tally(name='neutron_effective_dose_on_3D_mesh')

# converts the tally result into a VTK file
write_mesh_tally_to_vtk(
    tally=my_tally,
    filename = "heating_openmc_mesh.vtk",
)


write_mesh_tally_to_vtk(
    tally=my_tally1,
    filename = "neutron_openmc_mesh.vtk",
)
