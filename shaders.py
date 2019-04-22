# Imports, sorted alphabetically.

# Python packages

# Third-party packages

# Modules from this project
from shader import Shader


__all__ = (
    'create_block_shader'
)


def create_block_shader():
    return Shader([
            '''
#version 130
out vec3 vWorldPos;
out vec2 vTexCoord;
out vec3 vNormal;
out vec3 vColor;

void main()
{
        gl_Position = ftransform();
        vWorldPos = vec3(gl_ModelViewMatrix * gl_Vertex);
        vTexCoord = gl_MultiTexCoord0.st;
        vNormal = gl_Normal.xyz;
        vColor = gl_Color.rgb;
}
'''
        ], [
            '''
#version 130

in vec3 vWorldPos;
in vec2 vTexCoord;
in vec3 vNormal;
in vec3 vColor;

uniform sampler2D uDiffuse;
uniform vec3 uLightPos;

void main (void)
{
        vec3 light_dir = normalize(uLightPos - vWorldPos);
        vec3 diffuse = texture2D(uDiffuse, vTexCoord).rgb;
        float lambert = max(0.4, dot(vNormal, light_dir));
        vec4 final_color = vec4(lambert * diffuse * vColor, 1.0);
        gl_FragColor = final_color;
}
'''
        ])
