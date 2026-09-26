from .models import Certificate, CertificationSettings


def certificate_create(participant_name, participant_email, activity, workload):
    cs = CertificationSettings.get_solo()
    location = cs.default_location
    date = cs.default_date
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
            date=date,
            certifier_name=certifier_name,
            certifier_position=certifier_position,
            text=text,
            background_image=cs.default_background_image.name,
        )
        return ce
    return certificates[0]
