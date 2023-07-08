from dataclasses import dataclass
# from model.profile import Profile

@dataclass
class User:
    user_id: str

    # profile: Profile = Profile