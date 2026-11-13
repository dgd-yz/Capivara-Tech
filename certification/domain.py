from .models import Certificate, CertificationSettings
from .names import format_person_name


def certificate_create(participant_name, participant_email, activity, workload):
    participant_name = format_person_name(participant_name)
    cs = CertificationSettings.get_solo()
    location = cs.default_location
    certifier_name = cs.default_certifier_name
    certifier_position = cs.default_certifier_position
    text = cs.default_text

    certificates = Certificate.objects.filter(
        participant_name=participant_name,
        participant_email=participant_email,
        activity=activity,
    )

    if len(certificates) == 0:
        ce = Certificate.objects.create(
            participant_name=participant_name,
            participant_email=participant_email,
            activity=activity,
            workload=workload,
            location=location,
            certifier_name=certifier_name,
            certifier_position=certifier_position,
            text=text,
            background_image=cs.default_background_image.name,
        )
        return ce
    return certificates[0]
