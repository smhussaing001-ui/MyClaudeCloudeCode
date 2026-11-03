var out=[];
var c = app.project.items.addComp("_probe",100,100,1,1,30);
var l = c.layers.addSolid([0,0,0],"p",100,100,1);
var e = l.property("ADBE Effect Parade").addProperty("CC Particle World");
function walk(p, d){ for (var i=1;i<=p.numProperties;i++){ var q=p.property(i); out.push(new Array(d+1).join("  ")+q.name+" | "+q.matchName); if(q.propertyType!==PropertyType.PROPERTY) walk(q,d+1);} }
walk(e,0);
c.remove();
var f=new File("D:/Claude/SciSense/einstein-22min/m12/_probe.txt"); f.open("w"); f.write(out.join("\n")); f.close();
