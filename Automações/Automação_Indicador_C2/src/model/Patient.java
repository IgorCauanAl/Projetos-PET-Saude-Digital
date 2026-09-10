package model;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class Patient {

    private String name;
    private int dateOfBirth;
    private String enrollment;
    private String cpf;
    private int ma;
    private String linkedProfessional;
    private Indicators indicators;


}
